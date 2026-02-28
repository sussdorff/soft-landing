"""ReRoute — FastAPI backend for airline disruption management."""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, date as date_cls, datetime

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
from app.models import (
    BookingClass,
    DenyRequest,
    IngestEventRequest,
    LoyaltyTier,
    ResolveRequest,
    SimulateRequest,
    WishRequest,
)
from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.ports.repositories import DisruptionRepository
from app.seeds import scenario_snowstorm
from app.services.ahead_of_flight import AheadOfFlightEngine
from app.services.disruption_engine import DisruptionEngine
from app.services.option_generator import OptionGenerator
from app.services.gemini import GeminiGroundingService
from app.services.lufthansa import LufthansaClient
from app.services.state_manager import StateManager
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
    option_generator = OptionGenerator(flight_data, grounding, option_repo)

    # Disruption engine
    engine = DisruptionEngine(
        disruption_repo=disruption_repo,
        grounding=grounding,
        option_generator=option_generator,
        notification=notification,
    )

    # State manager (priority escalation + cascading impact)
    state_manager = StateManager(
        passenger_repo=passenger_repo,
        wish_repo=wish_repo,
        option_repo=option_repo,
        disruption_repo=disruption_repo,
        notification=notification,
    )

    # Ahead-of-flight engine
    ahead_engine = AheadOfFlightEngine(grounding, async_session)

    # Store on app.state for endpoint access
    app.state.ahead_engine = ahead_engine
    app.state.engine = engine
    app.state.flight_data = flight_data
    app.state.grounding = grounding
    app.state.notification = notification
    app.state.disruption_repo = disruption_repo
    app.state.passenger_repo = passenger_repo
    app.state.option_repo = option_repo
    app.state.wish_repo = wish_repo
    app.state.state_manager = state_manager
    app.state.option_generator = option_generator
    app.state.lh_client = lh_client

    # Auto-seed all scenarios if DB is empty
    if await disruption_repo.is_empty():
        from app.seeds import scenario_delay
        async with async_session() as session:
            await scenario_snowstorm.seed(session)
        async with async_session() as session:
            await scenario_delay.seed(session)
        await _generate_options_for_disruption(
            disruption_repo, option_generator, "MUC",
        )

    yield

    # Cleanup
    if lh_client:
        await lh_client.close()


async def _generate_options_for_disruption(
    disruption_repo: DisruptionRepository,
    option_generator: OptionGenerator,
    origin: str,
) -> None:
    """Generate options for all passengers linked to disruptions in the DB.

    Called after seeding to run the full OptionGenerator pipeline
    (LH API / Gemini if configured, static fallback otherwise).
    """
    disruptions = await disruption_repo.list_disruptions()
    for dis in disruptions:
        pax_list = await disruption_repo.get_disruption_passengers(dis.id)
        for pax in pax_list:
            await option_generator.generate_options(
                dis.id,
                pax.id,
                dis.type,
                dis.destination,
                origin=origin,
                loyalty_tier=pax.loyalty_tier,
                booking_class=pax.booking_class,
            )


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
    """Seed a disruption scenario additively (without wiping the DB).

    If the scenario already exists, returns 409 unless reset=true.
    When reset=true, deletes only that scenario's data before re-seeding.
    """
    disruption_repo = request.app.state.disruption_repo
    option_generator = request.app.state.option_generator

    # Map scenario name → (seed function, expected disruption IDs, origin)
    scenario_map = _get_scenario_map()
    if req.scenario not in scenario_map:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}. Available: {list(scenario_map)}")

    seed_fn, expected_ids, origin, _legacy = scenario_map[req.scenario]

    # Check if scenario already exists (including legacy IDs)
    all_known_ids = expected_ids + scenario_map[req.scenario][3]  # legacy IDs
    existing = [
        dis_id for dis_id in all_known_ids
        if await disruption_repo.get_disruption(dis_id) is not None
    ]
    if existing and not req.reset:
        raise HTTPException(
            409,
            f"Scenario '{req.scenario}' already seeded ({len(existing)} disruptions). "
            f"Use reset=true to re-seed.",
        )

    # If resetting, delete this scenario's data (current + legacy IDs)
    if existing and req.reset:
        await _delete_scenario_data(existing)

    # Seed the scenario
    async with async_session() as seed_session:
        result = await seed_fn(seed_session)

    # result is either a single ID (str) or list of IDs
    dis_ids = result if isinstance(result, list) else [result]

    # Generate options for the newly seeded disruptions
    for dis_id in dis_ids:
        dis = await disruption_repo.get_disruption(dis_id)
        if not dis:
            continue
        pax_list = await disruption_repo.get_disruption_passengers(dis_id)
        for pax in pax_list:
            await option_generator.generate_options(
                dis_id,
                pax.id,
                dis.type,
                dis.destination,
                origin=origin,
                loyalty_tier=pax.loyalty_tier,
                booking_class=pax.booking_class,
            )

    # Send WS notifications for all seeded disruptions
    notification = request.app.state.notification
    seeded_disruptions = []
    for dis_id in dis_ids:
        dis = await disruption_repo.get_disruption(dis_id)
        if not dis:
            continue
        seeded_disruptions.append(dis)
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

    return [d.model_dump(by_alias=True, mode="json") for d in seeded_disruptions]


def _get_scenario_map():
    """Return mapping: scenario → (seed_fn, expected_ids, origin, legacy_ids)."""
    from app.seeds import scenario_diversion, scenario_delay

    return {
        "munich_snowstorm": (
            scenario_snowstorm.seed,
            scenario_snowstorm.DISRUPTION_IDS,
            "MUC",
            scenario_snowstorm.LEGACY_IDS,
        ),
        "diversion": (
            scenario_diversion.seed,
            [scenario_diversion.DISRUPTION_ID],
            "NUE",
            [],
        ),
        "delay": (
            scenario_delay.seed,
            [scenario_delay.DISRUPTION_ID],
            "MUC",
            [],
        ),
    }


async def _delete_scenario_data(disruption_ids: list[str]) -> None:
    """Delete all data associated with the given disruption IDs.

    Cascading delete: disruption → disruption_passengers, and the
    linked passengers → segments, options, wishes.
    """
    from sqlalchemy import delete, select

    from app.db.tables import (
        DisruptionPassengerRow,
        DisruptionRow,
        OptionRow,
        PassengerRow,
        SegmentRow,
        WishRow,
    )

    async with async_session() as session:
        # Find all passenger IDs linked to these disruptions
        stmt = select(DisruptionPassengerRow.passenger_id).where(
            DisruptionPassengerRow.disruption_id.in_(disruption_ids)
        )
        pax_ids = list((await session.execute(stmt)).scalars().all())

        if pax_ids:
            # Delete wishes, options, segments for these passengers
            await session.execute(
                delete(WishRow).where(WishRow.passenger_id.in_(pax_ids))
            )
            await session.execute(
                delete(OptionRow).where(OptionRow.passenger_id.in_(pax_ids))
            )
            await session.execute(
                delete(SegmentRow).where(SegmentRow.passenger_id.in_(pax_ids))
            )

        # Delete disruption-passenger links
        await session.execute(
            delete(DisruptionPassengerRow).where(
                DisruptionPassengerRow.disruption_id.in_(disruption_ids)
            )
        )

        if pax_ids:
            # Delete passengers
            await session.execute(
                delete(PassengerRow).where(PassengerRow.id.in_(pax_ids))
            )

        # Delete disruptions
        await session.execute(
            delete(DisruptionRow).where(DisruptionRow.id.in_(disruption_ids))
        )

        await session.commit()


@app.post("/disruptions/{disruption_id}/generate-options")
async def generate_options_for_disruption(disruption_id: str, request: Request):
    """Generate options for all passengers of a disruption that don't have options yet."""
    disruption_repo = request.app.state.disruption_repo
    option_repo = request.app.state.option_repo
    option_generator = request.app.state.option_generator

    dis = await disruption_repo.get_disruption(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")

    pax_list = await disruption_repo.get_disruption_passengers(disruption_id)
    generated = 0
    for pax in pax_list:
        existing = await option_repo.get_passenger_options(pax.id)
        if existing:
            continue
        await option_generator.generate_options(
            disruption_id,
            pax.id,
            dis.type,
            dis.destination,
            origin=dis.origin,
            loyalty_tier=pax.loyalty_tier,
            booking_class=pax.booking_class,
        )
        generated += 1

    return {"disruptionId": disruption_id, "passengersProcessed": generated, "alreadyHadOptions": len(pax_list) - generated}


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

    if await request.app.state.wish_repo.has_pending_wish(passenger_id, req.disruption_id):
        raise HTTPException(409, "Passenger already has a pending wish for this disruption")

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

    sm: StateManager = request.app.state.state_manager
    result = await sm.handle_approval(wish.id, req.disruption_id)
    if not result.approved_wish:
        raise HTTPException(500, "Failed to approve wish")

    return result.approved_wish.model_dump(by_alias=True, mode="json")


# --- Wishes ---

@app.get("/wishes")
async def list_wishes(request: Request, disruption_id: str = Query(None)):
    result = await request.app.state.wish_repo.list_wishes(disruption_id=disruption_id)
    return [w.model_dump(by_alias=True, mode="json") for w in result]


@app.get("/wishes/{wish_id}")
async def get_wish(wish_id: str, request: Request):
    wish = await request.app.state.wish_repo.get_wish(wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")
    return wish.model_dump(by_alias=True, mode="json")


@app.post("/wishes/{wish_id}/approve")
async def approve_wish(
    wish_id: str,
    request: Request,
    disruption_id: str = Query(None, alias="disruptionId"),
):
    # Look up disruption_id from the wish if not provided
    if not disruption_id:
        wish = await request.app.state.wish_repo.get_wish(wish_id)
        if not wish:
            raise HTTPException(404, "Wish not found")
        disruption_id = wish.disruption_id

    sm: StateManager = request.app.state.state_manager
    result = await sm.handle_approval(wish_id, disruption_id)
    if result.rejected_reason == "option_unavailable":
        raise HTTPException(409, "Option is no longer available")
    if not result.approved_wish:
        raise HTTPException(404, "Wish not found")

    return {
        "wish": result.approved_wish.model_dump(by_alias=True, mode="json"),
        "affectedPassengerIds": result.affected_passenger_ids,
    }


@app.get("/wishes/{wish_id}/impact-preview")
async def preview_wish_impact(
    wish_id: str,
    request: Request,
    disruption_id: str = Query(None, alias="disruptionId"),
):
    if not disruption_id:
        wish = await request.app.state.wish_repo.get_wish(wish_id)
        if not wish:
            raise HTTPException(404, "Wish not found")
        disruption_id = wish.disruption_id

    sm: StateManager = request.app.state.state_manager
    return await sm.preview_impact(wish_id, disruption_id)


@app.post("/wishes/{wish_id}/deny")
async def deny_wish(wish_id: str, req: DenyRequest, request: Request):
    # Look up the wish first to get disruption_id and passenger_id
    wish = await request.app.state.wish_repo.get_wish(wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")

    sm: StateManager = request.app.state.state_manager
    denied = await sm.handle_denial(
        wish_id, wish.disruption_id, wish.passenger_id, reason=req.reason,
    )
    if not denied:
        raise HTTPException(404, "Wish not found")

    return denied.model_dump(by_alias=True, mode="json")


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


# --- Disruption explanation (Gemini Search grounding) ---

@app.get("/flights/{flight_number}/explain-disruption")
async def explain_flight_disruption(request: Request, flight_number: str):
    """Explain in clear language why a disruption is happening for a flight.

    Looks up the most recent disruption for the given flight number and
    uses Gemini with Google Search grounding to generate a real-time,
    passenger-friendly explanation.
    """
    dis = await request.app.state.disruption_repo.find_disruption_by_flight(flight_number)
    if not dis:
        raise HTTPException(404, f"No disruption found for flight {flight_number}")

    grounding: GroundingPort = request.app.state.grounding
    explanation = await grounding.explain_disruption(
        disruption_type=dis.type.value,
        flight_number=dis.flight_number,
        origin=dis.origin,
        destination=dis.destination,
        raw_reason=dis.reason,
    )

    return {
        "flightNumber": dis.flight_number,
        "disruptionId": dis.id,
        "disruptionType": dis.type.value,
        "origin": dis.origin,
        "destination": dis.destination,
        "reason": dis.reason,
        "explanation": explanation,
    }


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


# --- Rebook options search ---

@app.get("/rebook-options")
async def search_rebook_options(
    request: Request,
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    earliest: str = Query(None),
    booking_class: BookingClass = Query(BookingClass.Y),
    loyalty_tier: LoyaltyTier = Query(LoyaltyTier.NONE),
):
    """Search for rebook flight candidates.

    Returns flights sorted by departure time with seat availability
    checked for the first 3 results.
    """
    if earliest:
        try:
            earliest_dt = datetime.fromisoformat(earliest)
            if earliest_dt.tzinfo is None:
                earliest_dt = earliest_dt.replace(tzinfo=UTC)
        except ValueError:
            raise HTTPException(400, f"Invalid earliest datetime: {earliest}")
    else:
        earliest_dt = datetime.now(tz=UTC)

    gen = request.app.state.option_generator
    candidates = await gen.search_rebook_candidates(
        origin=origin.upper(),
        destination=destination.upper(),
        earliest=earliest_dt,
        booking_class=booking_class,
        loyalty_tier=loyalty_tier,
    )
    return [c.model_dump(by_alias=True, mode="json") for c in candidates]


# --- Ahead-of-Flight Intelligence ---

@app.get("/ahead-of-flight")
async def get_ahead_of_flight_briefings(
    request: Request,
    hours: int = Query(6, ge=1, le=48),
):
    """Get pre-flight intelligence briefings for upcoming flights.

    Scans flights departing within the given time window and returns
    briefings with weather, disruption context, and passenger risk data.
    """
    engine: AheadOfFlightEngine = request.app.state.ahead_engine
    briefings = await engine.scan_upcoming_flights(hours_ahead=hours)
    return [b.model_dump(by_alias=True, mode="json") for b in briefings]


@app.get("/ahead-of-flight/{flight_number}")
async def get_flight_briefing(
    request: Request,
    flight_number: str,
    date: str = Query(None),
):
    """Get a pre-flight intelligence briefing for a specific flight."""
    engine: AheadOfFlightEngine = request.app.state.ahead_engine
    flight_date = date or date_cls.today().isoformat()
    briefing = await engine.get_flight_briefing(flight_number, flight_date)
    if not briefing:
        raise HTTPException(404, f"No passengers found for flight {flight_number}")
    return briefing.model_dump(by_alias=True, mode="json")


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
