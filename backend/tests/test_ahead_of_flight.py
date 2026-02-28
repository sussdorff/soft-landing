"""Tests for the Ahead-of-Flight Context Engine."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tables import PassengerRow, SegmentRow
from app.ports.grounding import GroundingPort
from app.services.ahead_of_flight import AheadOfFlightEngine, _compute_risk
from app.services.gemini import FlightContext


# --- Helpers ---

async def _seed_passenger(
    session: AsyncSession,
    pid: str,
    name: str,
    flight_number: str,
    origin: str = "MUC",
    destination: str = "FRA",
    departure_offset_hours: float = 2,
    loyalty_tier: str = "none",
    booking_class: str = "Y",
    extra_segments: list[dict] | None = None,
) -> None:
    """Seed a passenger with one segment (optionally more)."""
    now = datetime.now(tz=UTC)
    pax = PassengerRow(
        id=pid, name=name, booking_ref="ABC123",
        status="unaffected", priority=0,
        loyalty_tier=loyalty_tier, booking_class=booking_class,
    )
    session.add(pax)
    session.add(SegmentRow(
        passenger_id=pid,
        flight_number=flight_number,
        origin=origin,
        destination=destination,
        departure=now + timedelta(hours=departure_offset_hours),
        arrival=now + timedelta(hours=departure_offset_hours + 1),
        position=0,
    ))
    if extra_segments:
        for i, seg in enumerate(extra_segments, start=1):
            session.add(SegmentRow(
                passenger_id=pid,
                flight_number=seg["flight_number"],
                origin=seg.get("origin", "FRA"),
                destination=seg.get("destination", "JFK"),
                departure=now + timedelta(hours=departure_offset_hours + 2 + i),
                arrival=now + timedelta(hours=departure_offset_hours + 3 + i),
                position=i,
            ))
    await session.commit()


def _mock_grounding(context: FlightContext | None = None) -> GroundingPort:
    """Create a mock GroundingPort that returns the given FlightContext."""
    mock = AsyncMock(spec=GroundingPort)
    mock.get_flight_context.return_value = context or FlightContext()
    return mock


# --- Tests ---

@pytest.mark.asyncio
async def test_scan_upcoming_flights_empty(session_factory):
    """No flights → empty list."""
    grounding = _mock_grounding()
    engine = AheadOfFlightEngine(grounding, session_factory)

    result = await engine.scan_upcoming_flights(hours_ahead=6)
    assert result == []
    grounding.get_flight_context.assert_not_called()


@pytest.mark.asyncio
async def test_scan_upcoming_flights_returns_briefing(session_factory):
    """Passengers on a near-future flight produce a briefing."""
    async with session_factory() as session:
        await _seed_passenger(session, "p1", "Alice", "LH100", departure_offset_hours=2)
        await _seed_passenger(session, "p2", "Bob", "LH100", departure_offset_hours=2)

    ctx = FlightContext(
        weather_origin="Clear skies, 5°C",
        weather_destination="Overcast, 8°C",
        airport_status="Normal operations",
    )
    grounding = _mock_grounding(ctx)
    engine = AheadOfFlightEngine(grounding, session_factory)

    result = await engine.scan_upcoming_flights(hours_ahead=6)
    assert len(result) == 1

    briefing = result[0]
    assert briefing.flight_number == "LH100"
    assert briefing.origin == "MUC"
    assert briefing.destination == "FRA"
    assert briefing.passenger_count == 2
    assert briefing.vip_count == 0
    assert briefing.connection_count == 0
    assert briefing.risk_level == "low"
    assert briefing.weather_origin == "Clear skies, 5°C"


@pytest.mark.asyncio
async def test_scan_counts_vips(session_factory):
    """HON and Senator passengers are counted as VIPs."""
    async with session_factory() as session:
        await _seed_passenger(session, "p1", "VIP Alice", "LH200",
                              loyalty_tier="hon", booking_class="F")
        await _seed_passenger(session, "p2", "VIP Bob", "LH200",
                              loyalty_tier="sen", booking_class="J")
        await _seed_passenger(session, "p3", "Regular Carol", "LH200")

    grounding = _mock_grounding()
    engine = AheadOfFlightEngine(grounding, session_factory)

    result = await engine.scan_upcoming_flights(hours_ahead=6)
    assert len(result) == 1
    assert result[0].vip_count == 2
    assert result[0].passenger_count == 3


@pytest.mark.asyncio
async def test_scan_counts_connections(session_factory):
    """Passengers with onward segments are counted as connections."""
    async with session_factory() as session:
        # Put the connecting segment far in the future so it doesn't appear
        # as a separate flight in the 6h scan window
        await _seed_passenger(
            session, "p1", "Connecting Pax", "LH300",
            extra_segments=[{"flight_number": "LH301"}],
            departure_offset_hours=1,
        )
        await _seed_passenger(session, "p2", "Direct Pax", "LH300",
                              departure_offset_hours=1)

    grounding = _mock_grounding()
    engine = AheadOfFlightEngine(grounding, session_factory)

    # Use a narrow window that catches LH300 but not the connecting LH301
    result = await engine.scan_upcoming_flights(hours_ahead=3)
    # Filter to just LH300 for our assertions
    lh300 = [b for b in result if b.flight_number == "LH300"]
    assert len(lh300) == 1
    assert lh300[0].connection_count == 1
    assert lh300[0].passenger_count == 2


@pytest.mark.asyncio
async def test_scan_excludes_distant_flights(session_factory):
    """Flights beyond the time window are excluded."""
    async with session_factory() as session:
        await _seed_passenger(session, "p1", "Near", "LH400", departure_offset_hours=2)
        await _seed_passenger(session, "p2", "Far", "LH401", departure_offset_hours=10)

    grounding = _mock_grounding()
    engine = AheadOfFlightEngine(grounding, session_factory)

    result = await engine.scan_upcoming_flights(hours_ahead=6)
    assert len(result) == 1
    assert result[0].flight_number == "LH400"


@pytest.mark.asyncio
async def test_scan_sorts_high_risk_first(session_factory):
    """High-risk flights come before low-risk ones."""
    async with session_factory() as session:
        await _seed_passenger(session, "p1", "A", "LH500", departure_offset_hours=2)
        await _seed_passenger(session, "p2", "B", "LH501", departure_offset_hours=3)

    # LH500: calm weather, LH501: storm
    def _side_effect(flight_number, date):
        if flight_number == "LH501":
            return FlightContext(
                weather_origin="Heavy snowstorm expected",
                disruption_info="Multiple cancellations",
            )
        return FlightContext()

    grounding = _mock_grounding()
    grounding.get_flight_context.side_effect = _side_effect
    engine = AheadOfFlightEngine(grounding, session_factory)

    result = await engine.scan_upcoming_flights(hours_ahead=6)
    assert len(result) == 2
    assert result[0].flight_number == "LH501"
    assert result[0].risk_level == "high"
    assert result[1].flight_number == "LH500"
    assert result[1].risk_level == "low"


@pytest.mark.asyncio
async def test_get_flight_briefing_found(session_factory):
    """Single flight briefing returns data."""
    async with session_factory() as session:
        await _seed_passenger(session, "p1", "Alice", "LH600")

    ctx = FlightContext(weather_origin="Rain", airport_status="Minor delays")
    grounding = _mock_grounding(ctx)
    engine = AheadOfFlightEngine(grounding, session_factory)

    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    briefing = await engine.get_flight_briefing("LH600", today)
    assert briefing is not None
    assert briefing.flight_number == "LH600"
    assert briefing.passenger_count == 1
    assert briefing.weather_origin == "Rain"


@pytest.mark.asyncio
async def test_get_flight_briefing_not_found(session_factory):
    """Unknown flight returns None."""
    grounding = _mock_grounding()
    engine = AheadOfFlightEngine(grounding, session_factory)

    briefing = await engine.get_flight_briefing("XX999", "2026-01-01")
    assert briefing is None


# --- Risk computation tests ---

def test_risk_high_on_storm():
    assert _compute_risk(
        weather_origin="Heavy snowstorm",
        weather_destination="Clear",
        disruption_info="",
        vip_count=0,
        passenger_count=10,
    ) == "high"


def test_risk_high_on_disruption():
    assert _compute_risk(
        weather_origin="Clear",
        weather_destination="Clear",
        disruption_info="Flight cancelled due to strike",
        vip_count=0,
        passenger_count=10,
    ) == "high"


def test_risk_medium_on_delay():
    assert _compute_risk(
        weather_origin="Clear",
        weather_destination="Clear",
        disruption_info="Possible delay due to ATC",
        vip_count=0,
        passenger_count=10,
    ) == "medium"


def test_risk_medium_on_high_vip_ratio():
    assert _compute_risk(
        weather_origin="Clear",
        weather_destination="Clear",
        disruption_info="",
        vip_count=5,
        passenger_count=10,
    ) == "medium"


def test_risk_low_default():
    assert _compute_risk(
        weather_origin="Clear skies",
        weather_destination="Sunny",
        disruption_info="",
        vip_count=0,
        passenger_count=10,
    ) == "low"
