"""Tests for the Disruption Engine (port-based)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
)
from app.models import (
    BookingClass,
    DisruptionType,
    LoyaltyTier,
    Passenger,
    PassengerStatus,
    Segment,
)
from app.ports.grounding import GroundingPort
from app.ports.notification import NotificationPort
from app.ports.repositories import DisruptionRepository
from app.services.disruption_engine import DisruptionEngine


# --- Helper to seed a passenger with segments ---

async def _seed_passenger(
    session: AsyncSession,
    pid: str,
    name: str,
    flight_number: str,
    origin: str = "MUC",
    destination: str = "FRA",
) -> None:
    now = datetime.now(tz=UTC)
    pax = PassengerRow(
        id=pid, name=name, booking_ref="ABC123",
        status="unaffected", priority=1,
    )
    session.add(pax)
    session.add(SegmentRow(
        passenger_id=pid,
        flight_number=flight_number,
        origin=origin,
        destination=destination,
        departure=now + timedelta(hours=2),
        arrival=now + timedelta(hours=3),
        position=0,
    ))
    await session.commit()


def _make_passenger(pid: str, name: str = "Test") -> Passenger:
    """Create a minimal Passenger model for mock returns."""
    return Passenger(
        id=pid,
        name=name,
        booking_ref="ABC123",
        original_itinerary=[
            Segment(
                flight_number="LH456",
                origin="MUC",
                destination="FRA",
                departure=datetime.now(tz=UTC) + timedelta(hours=2),
                arrival=datetime.now(tz=UTC) + timedelta(hours=3),
            ),
        ],
        status=PassengerStatus.UNAFFECTED,
        loyalty_tier=LoyaltyTier.NONE,
        booking_class=BookingClass.Y,
    )


# --- Fixtures ---

@pytest.fixture
def mock_disruption_repo() -> DisruptionRepository:
    repo = AsyncMock(spec=DisruptionRepository)
    repo.find_affected_passengers = AsyncMock(return_value=[])
    repo.create_disruption = AsyncMock(return_value="dis-001")
    return repo


@pytest.fixture
def mock_grounding() -> GroundingPort:
    grounding = AsyncMock(spec=GroundingPort)
    grounding.explain_disruption = AsyncMock(
        return_value="A disruption has affected your flight.",
    )
    return grounding


@pytest.fixture
def mock_option_generator() -> AsyncMock:
    gen = AsyncMock()
    gen.generate_options = AsyncMock(return_value=[])
    return gen


@pytest.fixture
def mock_notification() -> NotificationPort:
    notif = AsyncMock(spec=NotificationPort)
    notif.send_to_passenger = AsyncMock()
    notif.send_to_dashboard = AsyncMock()
    return notif


@pytest.fixture
def engine(
    mock_disruption_repo,
    mock_grounding,
    mock_option_generator,
    mock_notification,
) -> DisruptionEngine:
    return DisruptionEngine(
        disruption_repo=mock_disruption_repo,
        grounding=mock_grounding,
        option_generator=mock_option_generator,
        notification=mock_notification,
    )


# --- classify_event tests ---

class TestClassifyEvent:
    def test_cancellation_by_status_code(self):
        raw = {"status_code": "CNL", "reason": ""}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.CANCELLATION

    def test_diversion_by_status_code(self):
        raw = {"status_code": "DVT", "reason": ""}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.DIVERSION

    def test_delay_by_status_code(self):
        raw = {"status_code": "DLY", "reason": ""}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.DELAY

    def test_gate_change_by_status_code(self):
        raw = {"status_code": "GCH", "reason": ""}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.GATE_CHANGE

    def test_cancellation_by_keyword(self):
        raw = {"reason": "Flight cancelled due to weather"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.CANCELLATION

    def test_diversion_by_keyword(self):
        raw = {"reason": "Aircraft diverted to alternate airport"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.DIVERSION

    def test_gate_change_by_keyword(self):
        raw = {"reason": "Gate change to B42"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.GATE_CHANGE

    def test_delay_by_keyword(self):
        raw = {"reason": "Delayed due to crew availability"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.DELAY

    def test_default_to_delay(self):
        raw = {"reason": "Unknown operational issue"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.DELAY

    def test_status_code_takes_precedence(self):
        raw = {"status_code": "CNL", "reason": "Delayed departure"}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.CANCELLATION

    def test_case_insensitive_status_code(self):
        raw = {"status_code": "cnl", "reason": ""}
        assert DisruptionEngine.classify_event(raw) == DisruptionType.CANCELLATION


# --- ingest_event tests ---

class TestIngestEvent:
    async def test_creates_disruption(
        self, engine, mock_disruption_repo, mock_grounding,
    ):
        pax = _make_passenger("pax-001", "Alice")
        mock_disruption_repo.find_affected_passengers.return_value = [pax]

        dis_id = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Flight cancelled due to weather",
            "status_code": "CNL",
        })

        assert dis_id == "dis-001"
        mock_disruption_repo.create_disruption.assert_called_once()
        call_kwargs = mock_disruption_repo.create_disruption.call_args.kwargs
        assert call_kwargs["disruption_type"] == DisruptionType.CANCELLATION
        assert call_kwargs["flight_number"] == "LH456"
        assert call_kwargs["affected_passenger_ids"] == ["pax-001"]

    async def test_calls_grounding_for_explanation(
        self, engine, mock_disruption_repo, mock_grounding,
    ):
        mock_disruption_repo.find_affected_passengers.return_value = []

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Heavy snowstorm",
            "status_code": "CNL",
        })

        mock_grounding.explain_disruption.assert_called_once_with(
            "cancellation", "LH456", "MUC", "FRA", "Heavy snowstorm",
        )
        # Explanation is passed to create_disruption
        call_kwargs = mock_disruption_repo.create_disruption.call_args.kwargs
        assert call_kwargs["explanation"] == "A disruption has affected your flight."

    async def test_generates_options_for_each_passenger(
        self, engine, mock_disruption_repo, mock_option_generator,
    ):
        pax1 = _make_passenger("pax-001", "Alice")
        pax2 = _make_passenger("pax-002", "Bob")
        mock_disruption_repo.find_affected_passengers.return_value = [pax1, pax2]

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        assert mock_option_generator.generate_options.call_count == 2
        calls = mock_option_generator.generate_options.call_args_list
        assert calls[0].args[:3] == ("dis-001", "pax-001", DisruptionType.CANCELLATION)
        assert calls[1].args[:3] == ("dis-001", "pax-002", DisruptionType.CANCELLATION)

    async def test_sends_dashboard_notification(
        self, engine, mock_disruption_repo, mock_notification,
    ):
        pax = _make_passenger("pax-001", "Alice")
        mock_disruption_repo.find_affected_passengers.return_value = [pax]

        dis_id = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        mock_notification.send_to_dashboard.assert_called_once()
        call_args = mock_notification.send_to_dashboard.call_args
        assert call_args.args[0] == dis_id
        assert call_args.args[1] == "disruption_created"
        assert call_args.args[2]["affectedPassengers"] == 1

    async def test_sends_passenger_notifications(
        self, engine, mock_disruption_repo, mock_notification,
    ):
        pax = _make_passenger("pax-001", "Alice")
        mock_disruption_repo.find_affected_passengers.return_value = [pax]

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        # Two calls per passenger: disruption_notification + options_ready
        assert mock_notification.send_to_passenger.call_count == 2
        pax_calls = mock_notification.send_to_passenger.call_args_list
        assert pax_calls[0].args[1] == "disruption_notification"
        assert pax_calls[1].args[1] == "options_ready"

    async def test_gate_change_still_generates_options(
        self, engine, mock_disruption_repo, mock_option_generator,
    ):
        """Gate change filtering is OptionGenerator's responsibility, not the engine's."""
        pax = _make_passenger("pax-001", "Alice")
        mock_disruption_repo.find_affected_passengers.return_value = [pax]

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Gate change to B42",
            "status_code": "GCH",
        })

        # Engine delegates to option generator regardless of type
        mock_option_generator.generate_options.assert_called_once()
        call_args = mock_option_generator.generate_options.call_args
        assert call_args.args[2] == DisruptionType.GATE_CHANGE

    async def test_no_passengers_no_options_or_pax_notifications(
        self, engine, mock_disruption_repo, mock_option_generator, mock_notification,
    ):
        mock_disruption_repo.find_affected_passengers.return_value = []

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        mock_option_generator.generate_options.assert_not_called()
        mock_notification.send_to_passenger.assert_not_called()
        # Dashboard still notified (disruption exists even if no passengers found)
        mock_notification.send_to_dashboard.assert_called_once()

    async def test_hub_disruption_multiple_flights(
        self, engine, mock_disruption_repo,
    ):
        """Two ingests for different flights produce two disruption IDs."""
        mock_disruption_repo.create_disruption.side_effect = ["dis-001", "dis-002"]
        mock_disruption_repo.find_affected_passengers.return_value = [
            _make_passenger("pax-001"),
        ]

        dis_id_1 = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })
        dis_id_2 = await engine.ingest_event({
            "flight_number": "LH1834",
            "origin": "MUC",
            "destination": "CDG",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        assert dis_id_1 != dis_id_2
        assert mock_disruption_repo.create_disruption.call_count == 2

    async def test_passes_loyalty_and_booking_to_option_generator(
        self, engine, mock_disruption_repo, mock_option_generator,
    ):
        pax = _make_passenger("pax-001")
        pax.loyalty_tier = LoyaltyTier.SENATOR
        pax.booking_class = BookingClass.C
        mock_disruption_repo.find_affected_passengers.return_value = [pax]

        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        call_kwargs = mock_option_generator.generate_options.call_args.kwargs
        assert call_kwargs["loyalty_tier"] == LoyaltyTier.SENATOR
        assert call_kwargs["booking_class"] == BookingClass.C
