"""ReRoute — FastAPI backend for airline disruption management."""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date as date_cls

from dotenv import load_dotenv

load_dotenv()  # Load .env before reading API keys

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.gemini_grounding import GeminiGroundingAdapter
from app.adapters.lufthansa_api import LufthansaAPIAdapter
from app.adapters.repositories import (
    SqlDisruptionRepository,
    SqlOptionRepository,
    SqlPassengerRepository,
    SqlWishRepository,
)
from app.adapters.static_data import StaticDataAdapter
from app.adapters.websocket_notification import WebSocketNotificationAdapter
from app.db.engine import async_session, init_db
from app.models import DenyRequest, IngestEventRequest, ResolveRequest, SimulateRequest, WishRequest
from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.seeds import scenario_snowstorm
from app.services.disruption_engine import DisruptionEngine
from app.services.gemini import GeminiGroundingService
from app.services.lufthansa import LufthansaClient
from app.models import compute_service_level
from app.ws import manager

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # --- Build adapters ---
    static = StaticDataAdapter()

    # Flight data: LH API if configured, otherwise static fallback
    flight_data: FlightDataPort
    lh_client: LufthansaClient | None = None
    if os.environ.get("LH_API_CLIENT_ID") and os.environ.get("LH_API_CLIENT_SECRET"):
        lh_client = LufthansaClient()
        flight_data = LufthansaAPIAdapter(lh_client)
        log.info("Lufthansa API enabled")
    else:
        flight_data = static
        log.warning("LH_API credentials not set — using static flight data")

    # Grounding: Gemini if configured, otherwise static fallback
    grounding: GroundingPort
    gemini_service: GeminiGroundingService | None = None
    if os.environ.get("GEMINI_API_KEY"):
        gemini_service = GeminiGroundingService()
        grounding = GeminiGroundingAdapter(gemini_service)
        log.info("Gemini Grounding enabled")
    else:
        grounding = static
        log.warning("GEMINI_API_KEY not set — using static grounding data")

    # Notification
    notification = WebSocketNotificationAdapter(manager)

    # Repositories
    disruption_repo = SqlDisruptionRepository(async_session)
    passenger_repo = SqlPassengerRepository(async_session)
    option_repo = SqlOptionRepository(async_session)
    wish_repo = SqlWishRepository(async_session)

    # OptionGenerator with injected ports
    from app.services.option_generator import OptionGenerator
    option_generator = OptionGenerator(flight_data, grounding, option_repo)

    # Disruption engine
    engine = DisruptionEngine(
        disruption_repo=disruption_repo,
        grounding=grounding,
        option_generator=option_generator,
        notification=notification,
    )

    # Store on app.state for endpoint access
    app.state.engine = engine
    app.state.flight_data = flight_data
    app.state.grounding = grounding
    app.state.notification = notification
    app.state.disruption_repo = disruption_repo
    app.state.passenger_repo = passenger_repo
    app.state.option_repo = option_repo
    app.state.wish_repo = wish_repo
    app.state.lh_client = lh_client

    # Auto-seed snowstorm scenario if DB is empty
    if await disruption_repo.is_empty():
        async with async_session() as session:
            await scenario_snowstorm.seed(session)

    yield

    # Cleanup
    if lh_client:
        await lh_client.close()


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


# --- Disruptions ---

@app.post("/disruptions/simulate")
async def simulate_disruption(req: SimulateRequest, request: Request):
    from app.db.engine import drop_db

    await drop_db()
    await init_db()

    async with async_session() as seed_session:
        if req.scenario == "diversion":
            from app.seeds import scenario_diversion
            dis_id = await scenario_diversion.seed(seed_session)
        else:
            dis_id = await scenario_snowstorm.seed(seed_session)

    dis = await request.app.state.disruption_repo.get_disruption(dis_id)
    if not dis:
        raise HTTPException(500, "Failed to seed scenario")

    # Send WS notifications for the seeded disruption
    notification = request.app.state.notification
    await notification.send_to_dashboard(dis.id, "disruption_created", {
        "disruptionId": dis.id,
        "type": dis.type.value,
        "flightNumber": dis.flight_number,
        "affectedPassengers": len(dis.affected_passenger_ids),
    })
    for pax_id in dis.affected_passenger_ids:
        await notification.send_to_passenger(pax_id, "disruption_notification", {
            "disruptionId": dis.id,
            "type": dis.type.value,
            "flightNumber": dis.flight_number,
        })
        await notification.send_to_passenger(pax_id, "options_ready", {
            "disruptionId": dis.id,
            "passengerId": pax_id,
        })

    return dis.model_dump(by_alias=True, mode="json")


@app.post("/disruptions/ingest")
async def ingest_disruption(req: IngestEventRequest, request: Request):
    """Ingest a raw disruption event (simulates MQTT delivery).

    The engine classifies the event, finds affected passengers,
    generates options, and sends WebSocket notifications.
    """
    dis_id = await request.app.state.engine.ingest_event(req.model_dump())
    dis = await request.app.state.disruption_repo.get_disruption(dis_id)
    if not dis:
        raise HTTPException(500, "Failed to process event")
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions")
async def list_disruptions(request: Request):
    disruptions = await request.app.state.disruption_repo.list_disruptions()
    return [d.model_dump(by_alias=True, mode="json") for d in disruptions]


@app.get("/disruptions/{disruption_id}")
async def get_disruption(disruption_id: str, request: Request):
    dis = await request.app.state.disruption_repo.get_disruption(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions/{disruption_id}/passengers")
async def get_disruption_passengers(disruption_id: str, request: Request):
    dis = await request.app.state.disruption_repo.get_disruption(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    pax_list = await request.app.state.disruption_repo.get_disruption_passengers(disruption_id)
    return [p.model_dump(by_alias=True, mode="json") for p in pax_list]


@app.get("/disruptions/{disruption_id}/options")
async def get_disruption_options(disruption_id: str, request: Request):
    dis = await request.app.state.disruption_repo.get_disruption(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    opts_map = await request.app.state.option_repo.get_disruption_options(disruption_id)
    return {
        pid: [o.model_dump(by_alias=True, mode="json") for o in opts]
        for pid, opts in opts_map.items()
    }


# --- Passengers ---

@app.get("/passengers/{passenger_id}/disruptions")
async def get_passenger_disruptions(passenger_id: str, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    disruptions = await request.app.state.passenger_repo.get_passenger_disruptions(passenger_id)
    return [d.model_dump(by_alias=True, mode="json") for d in disruptions]


@app.get("/passengers/{passenger_id}/options")
async def get_passenger_options(passenger_id: str, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    opts = await request.app.state.option_repo.get_passenger_options(passenger_id)
    return [o.model_dump(by_alias=True, mode="json") for o in opts]


@app.get("/passengers/{passenger_id}/status")
async def get_passenger_status(passenger_id: str, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
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
async def get_passenger_profile(passenger_id: str, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    pax_wishes = await request.app.state.wish_repo.list_wishes()
    pax_wishes = [w for w in pax_wishes if w.passenger_id == passenger_id]
    pax_disruptions = await request.app.state.passenger_repo.get_passenger_disruptions(passenger_id)
    opts = await request.app.state.option_repo.get_passenger_options(passenger_id)
    return {
        "passenger": pax.model_dump(by_alias=True, mode="json"),
        "options": [o.model_dump(by_alias=True, mode="json") for o in opts],
        "wishes": [w.model_dump(by_alias=True, mode="json") for w in pax_wishes],
        "disruptions": [d.model_dump(by_alias=True, mode="json") for d in pax_disruptions],
    }


@app.get("/passengers/{passenger_id}/service-level")
async def get_passenger_service_level(passenger_id: str, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    sl = compute_service_level(pax.loyalty_tier, pax.booking_class)
    return sl.model_dump(by_alias=True, mode="json")


@app.post("/passengers/{passenger_id}/wish")
async def submit_wish(passenger_id: str, req: WishRequest, request: Request):
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")

    wish = await request.app.state.wish_repo.create_wish(
        passenger_id=passenger_id,
        disruption_id=req.disruption_id,
        selected_option_id=req.selected_option_id,
        ranked_option_ids=req.ranked_option_ids,
    )

    await request.app.state.notification.send_to_dashboard(req.disruption_id, "wish_submitted", {
        "wishId": wish.id,
        "passengerId": passenger_id,
        "selectedOptionId": req.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


@app.post("/passengers/{passenger_id}/resolve")
async def resolve_passenger(passenger_id: str, req: ResolveRequest, request: Request):
    """Atomically create and approve a wish for a passenger (gate agent shortcut)."""
    pax = await request.app.state.passenger_repo.get_passenger(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")

    wish = await request.app.state.wish_repo.create_wish(
        passenger_id=passenger_id,
        disruption_id=req.disruption_id,
        selected_option_id=req.selected_option_id,
        ranked_option_ids=[req.selected_option_id],
    )

    await request.app.state.notification.send_to_dashboard(req.disruption_id, "wish_submitted", {
        "wishId": wish.id,
        "passengerId": passenger_id,
        "selectedOptionId": req.selected_option_id,
    })

    wish = await request.app.state.wish_repo.approve_wish(wish.id)
    if not wish:
        raise HTTPException(500, "Failed to approve wish")

    await request.app.state.notification.send_to_passenger(passenger_id, "wish_approved", {
        "wishId": wish.id,
        "selectedOptionId": wish.selected_option_id,
    })

    return wish.model_dump(by_alias=True, mode="json")


# --- Wishes ---

@app.get("/wishes")
async def list_wishes(request: Request, disruption_id: str = Query(None)):
    result = await request.app.state.wish_repo.list_wishes(disruption_id=disruption_id)
    return [w.model_dump(by_alias=True, mode="json") for w in result]


@app.post("/wishes/{wish_id}/approve")
async def approve_wish(wish_id: str, request: Request):
    wish = await request.app.state.wish_repo.approve_wish(wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")

    await request.app.state.notification.send_to_passenger(wish.passenger_id, "wish_approved", {
        "wishId": wish.id,
        "selectedOptionId": wish.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


@app.post("/wishes/{wish_id}/deny")
async def deny_wish(wish_id: str, req: DenyRequest, request: Request):
    wish = await request.app.state.wish_repo.deny_wish(wish_id, req.reason)
    if not wish:
        raise HTTPException(404, "Wish not found")

    await request.app.state.notification.send_to_passenger(wish.passenger_id, "wish_denied", {
        "wishId": wish.id,
        "reason": req.reason,
    })
    return wish.model_dump(by_alias=True, mode="json")


# --- Lufthansa API ---

@app.get("/api/lounges/{airport_code}")
async def get_airport_lounges(request: Request, airport_code: str, tier: str = Query(None)):
    flight_data = request.app.state.flight_data
    tier_map = {"hon": "HON", "sen": "SEN", "ftl": "FTL"}
    tier_code = tier_map.get(tier) if tier else None
    data = await flight_data.get_lounges(airport_code, tier_code=tier_code)
    return data


@app.get("/api/flights/{flight_number}/status")
async def get_flight_status(request: Request, flight_number: str, date: str = Query(None)):
    flight_data = request.app.state.flight_data
    flight_date = date or date_cls.today().isoformat()
    return await flight_data.get_flight_status(flight_number, flight_date)


@app.get("/api/schedules/{origin}/{destination}")
async def get_schedules(request: Request, origin: str, destination: str, date: str = Query(None)):
    flight_data = request.app.state.flight_data
    flight_date = date or date_cls.today().isoformat()
    return await flight_data.get_schedules(origin, destination, flight_date)


# --- Flight context (Gemini Search grounding) ---

@app.get("/flights/{flight_number}/context")
async def get_flight_context(request: Request, flight_number: str, date: str = Query(None)):
    """Get contextual intelligence about a flight (weather, NOTAMs, events).

    Uses Gemini Search grounding for real-time data, or static fallback.
    """
    grounding = request.app.state.grounding
    flight_date = date or date_cls.today().isoformat()
    ctx = await grounding.get_flight_context(flight_number, flight_date)
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
