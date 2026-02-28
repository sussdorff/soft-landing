"""ReRoute — FastAPI backend for airline disruption management."""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date as date_cls

from dotenv import load_dotenv

load_dotenv()  # Load .env before reading API keys

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app import store
from app.db.engine import async_session, get_session, init_db
from app.models import DenyRequest, IngestEventRequest, SimulateRequest, WishRequest
from app.seeds import scenario_snowstorm
from app.services.disruption_engine import DisruptionEngine
from app.services.gemini import FlightContext, GeminiGroundingService
from app.services.lufthansa import LufthansaClient
from app.ws import manager

log = logging.getLogger(__name__)

# --- External service instances (None when API keys missing) ---

_gemini: GeminiGroundingService | None = None
if os.environ.get("GEMINI_API_KEY"):
    _gemini = GeminiGroundingService()
    log.info("Gemini Grounding enabled (hotels, transport, explanations)")
else:
    log.warning("GEMINI_API_KEY not set — Gemini disabled, using fallback data")

_lh_client: LufthansaClient | None = None
if os.environ.get("LH_API_CLIENT_ID") and os.environ.get("LH_API_CLIENT_SECRET"):
    _lh_client = LufthansaClient()
    log.info("Lufthansa API enabled")
else:
    log.warning("LH_API credentials not set — LH API disabled, using static data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Auto-seed snowstorm scenario if DB is empty
    async with async_session() as session:
        if await store.is_empty(session):
            await scenario_snowstorm.seed(session)
    yield


app = FastAPI(
    title="ReRoute API",
    description="Passenger disruption management for Lufthansa hackathon",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Disruption engine instance (shared across requests)
engine = DisruptionEngine(async_session, manager, gemini=_gemini, lh_client=_lh_client)


# --- Disruptions ---

@app.post("/disruptions/simulate")
async def simulate_disruption(req: SimulateRequest, session: AsyncSession = Depends(get_session)):
    from app.db.engine import drop_db

    await drop_db()
    await init_db()

    async with async_session() as seed_session:
        if req.scenario == "diversion":
            from app.seeds import scenario_diversion
            dis_id = await scenario_diversion.seed(seed_session)
        else:
            dis_id = await scenario_snowstorm.seed(seed_session)

    dis = await store.get_disruption(session, dis_id)
    if not dis:
        raise HTTPException(500, "Failed to seed scenario")

    # Send WS notifications for the seeded disruption
    await manager.send_to_dashboard(dis.id, "disruption_created", {
        "disruptionId": dis.id,
        "type": dis.type.value,
        "flightNumber": dis.flight_number,
        "affectedPassengers": len(dis.affected_passenger_ids),
    })
    for pax_id in dis.affected_passenger_ids:
        await manager.send_to_passenger(pax_id, "disruption_notification", {
            "disruptionId": dis.id,
            "type": dis.type.value,
            "flightNumber": dis.flight_number,
        })
        await manager.send_to_passenger(pax_id, "options_ready", {
            "disruptionId": dis.id,
            "passengerId": pax_id,
        })

    return dis.model_dump(by_alias=True, mode="json")


@app.post("/disruptions/ingest")
async def ingest_disruption(req: IngestEventRequest):
    """Ingest a raw disruption event (simulates MQTT delivery).

    The engine classifies the event, finds affected passengers,
    generates options, and sends WebSocket notifications.
    """
    dis_id = await engine.ingest_event(req.model_dump())
    async with async_session() as session:
        dis = await store.get_disruption(session, dis_id)
    if not dis:
        raise HTTPException(500, "Failed to process event")
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions/{disruption_id}")
async def get_disruption(disruption_id: str, session: AsyncSession = Depends(get_session)):
    dis = await store.get_disruption(session, disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions/{disruption_id}/passengers")
async def get_disruption_passengers(disruption_id: str, session: AsyncSession = Depends(get_session)):
    dis = await store.get_disruption(session, disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    pax_list = await store.get_disruption_passengers(session, disruption_id)
    return [p.model_dump(by_alias=True, mode="json") for p in pax_list]


# --- Passengers ---

@app.get("/passengers/{passenger_id}/disruptions")
async def get_passenger_disruptions(passenger_id: str, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    disruptions = await store.get_passenger_disruptions(session, passenger_id)
    return [d.model_dump(by_alias=True, mode="json") for d in disruptions]


@app.get("/passengers/{passenger_id}/options")
async def get_passenger_options(passenger_id: str, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    opts = await store.get_passenger_options(session, passenger_id)
    return [o.model_dump(by_alias=True, mode="json") for o in opts]


@app.get("/passengers/{passenger_id}/status")
async def get_passenger_status(passenger_id: str, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    return {
        "passengerId": pax.id,
        "name": pax.name,
        "status": pax.status,
        "denialCount": pax.denial_count,
        "priority": pax.priority,
    }


@app.get("/passengers/{passenger_id}/profile")
async def get_passenger_profile(passenger_id: str, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    pax_wishes = await store.list_wishes(session)
    pax_wishes = [w for w in pax_wishes if w.passenger_id == passenger_id]
    pax_disruptions = await store.get_passenger_disruptions(session, passenger_id)
    opts = await store.get_passenger_options(session, passenger_id)
    return {
        "passenger": pax.model_dump(by_alias=True, mode="json"),
        "options": [o.model_dump(by_alias=True, mode="json") for o in opts],
        "wishes": [w.model_dump(by_alias=True, mode="json") for w in pax_wishes],
        "disruptions": [d.model_dump(by_alias=True, mode="json") for d in pax_disruptions],
    }


@app.get("/passengers/{passenger_id}/service-level")
async def get_passenger_service_level(passenger_id: str, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    sl = store.compute_service_level(pax.loyalty_tier, pax.booking_class)
    return sl.model_dump(by_alias=True, mode="json")


@app.post("/passengers/{passenger_id}/wish")
async def submit_wish(passenger_id: str, req: WishRequest, session: AsyncSession = Depends(get_session)):
    pax = await store.get_passenger(session, passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")

    wish = await store.create_wish(
        session,
        passenger_id=passenger_id,
        disruption_id=req.disruption_id,
        selected_option_id=req.selected_option_id,
        ranked_option_ids=req.ranked_option_ids,
    )

    await manager.send_to_dashboard(req.disruption_id, "wish_submitted", {
        "wishId": wish.id,
        "passengerId": passenger_id,
        "selectedOptionId": req.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


# --- Wishes ---

@app.get("/wishes")
async def list_wishes(disruption_id: str = Query(None), session: AsyncSession = Depends(get_session)):
    result = await store.list_wishes(session, disruption_id=disruption_id)
    return [w.model_dump(by_alias=True, mode="json") for w in result]


@app.post("/wishes/{wish_id}/approve")
async def approve_wish(wish_id: str, session: AsyncSession = Depends(get_session)):
    wish = await store.approve_wish(session, wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")

    await manager.send_to_passenger(wish.passenger_id, "wish_approved", {
        "wishId": wish.id,
        "selectedOptionId": wish.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


@app.post("/wishes/{wish_id}/deny")
async def deny_wish(wish_id: str, req: DenyRequest, session: AsyncSession = Depends(get_session)):
    wish = await store.deny_wish(session, wish_id, req.reason)
    if not wish:
        raise HTTPException(404, "Wish not found")

    await manager.send_to_passenger(wish.passenger_id, "wish_denied", {
        "wishId": wish.id,
        "reason": req.reason,
    })
    return wish.model_dump(by_alias=True, mode="json")


# --- Lufthansa API ---

@app.get("/api/lounges/{airport_code}")
async def get_airport_lounges(airport_code: str, tier: str = Query(None)):
    if not _lh_client:
        raise HTTPException(503, "Lufthansa API not configured")
    tier_map = {"hon": "HON", "sen": "SEN", "ftl": "FTL"}
    tier_code = tier_map.get(tier) if tier else None
    data = await _lh_client.get_lounges(airport_code, tier_code=tier_code)
    return data


@app.get("/api/flights/{flight_number}/status")
async def get_flight_status(flight_number: str, date: str = Query(None)):
    if not _lh_client:
        raise HTTPException(503, "Lufthansa API not configured")
    flight_date = date or date_cls.today().isoformat()
    return await _lh_client.get_flight_status(flight_number, flight_date)


@app.get("/api/schedules/{origin}/{destination}")
async def get_schedules(origin: str, destination: str, date: str = Query(None)):
    if not _lh_client:
        raise HTTPException(503, "Lufthansa API not configured")
    flight_date = date or date_cls.today().isoformat()
    return await _lh_client.get_schedules(origin, destination, flight_date)


# --- Flight context (Gemini Search grounding) ---

@app.get("/flights/{flight_number}/context")
async def get_flight_context(flight_number: str, date: str = Query(None)):
    """Get contextual intelligence about a flight (weather, NOTAMs, events).

    Uses Gemini Search grounding for real-time data.
    """
    if _gemini is None:
        raise HTTPException(503, "Gemini not configured")
    flight_date = date or date_cls.today().isoformat()
    ctx: FlightContext = await _gemini.get_flight_context(flight_number, flight_date)
    return asdict(ctx)


# --- WebSocket ---

@app.websocket("/ws/passenger/{passenger_id}")
async def ws_passenger(ws: WebSocket, passenger_id: str):
    await manager.connect_passenger(passenger_id, ws)
    try:
        while True:
            await ws.receive_text()
            await ws.send_text('{"type":"ack","data":{}}')
    except WebSocketDisconnect:
        manager.disconnect_passenger(passenger_id, ws)


@app.websocket("/ws/dashboard/{disruption_id}")
async def ws_dashboard(ws: WebSocket, disruption_id: str):
    await manager.connect_dashboard(disruption_id, ws)
    try:
        while True:
            await ws.receive_text()
            await ws.send_text('{"type":"ack","data":{}}')
    except WebSocketDisconnect:
        manager.disconnect_dashboard(disruption_id, ws)
