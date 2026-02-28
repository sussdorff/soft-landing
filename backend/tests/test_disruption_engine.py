"""Tests for the Disruption Engine."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
)
from app.models import DisruptionType
from app.services.disruption_engine import DisruptionEngine
from app.ws import ConnectionManager


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


# --- find_affected_passengers tests ---

class TestFindAffectedPassengers:
    async def test_finds_passenger_on_flight(self, db_session: AsyncSession):
        await _seed_passenger(db_session, "pax-001", "Alice", "LH456")
        passengers = await DisruptionEngine.find_affected_passengers(
            db_session, "LH456",
        )
        assert len(passengers) == 1
        assert passengers[0].id == "pax-001"

    async def test_ignores_passenger_on_different_flight(self, db_session: AsyncSession):
        await _seed_passenger(db_session, "pax-001", "Alice", "LH456")
        await _seed_passenger(db_session, "pax-002", "Bob", "LH999")
        passengers = await DisruptionEngine.find_affected_passengers(
            db_session, "LH456",
        )
        assert len(passengers) == 1
        assert passengers[0].id == "pax-001"

    async def test_finds_multiple_passengers(self, db_session: AsyncSession):
        await _seed_passenger(db_session, "pax-001", "Alice", "LH456")
        await _seed_passenger(db_session, "pax-002", "Bob", "LH456")
        passengers = await DisruptionEngine.find_affected_passengers(
            db_session, "LH456",
        )
        assert len(passengers) == 2

    async def test_empty_when_no_match(self, db_session: AsyncSession):
        await _seed_passenger(db_session, "pax-001", "Alice", "LH456")
        passengers = await DisruptionEngine.find_affected_passengers(
            db_session, "LH999",
        )
        assert len(passengers) == 0


# --- ingest_event tests ---

class TestIngestEvent:
    async def test_creates_disruption(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        # Seed a passenger first
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        dis_id = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Flight cancelled due to weather",
            "status_code": "CNL",
            "explanation": "Heavy snowstorm.",
        })

        # Verify disruption was created
        async with session_factory() as session:
            row = await session.get(DisruptionRow, dis_id)
            assert row is not None
            assert row.type == "cancellation"
            assert row.flight_number == "LH456"

    async def test_links_affected_passengers(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")
            await _seed_passenger(session, "pax-002", "Bob", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        dis_id = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        async with session_factory() as session:
            stmt = select(DisruptionPassengerRow).where(
                DisruptionPassengerRow.disruption_id == dis_id,
            )
            links = (await session.execute(stmt)).scalars().all()
            assert len(links) == 2

    async def test_generates_options(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        async with session_factory() as session:
            stmt = select(OptionRow).where(OptionRow.passenger_id == "pax-001")
            options = (await session.execute(stmt)).scalars().all()
            assert len(options) >= 2  # At least rebook + hotel

    async def test_sends_websocket_notifications(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        dis_id = await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        # Dashboard notification
        mock_ws_manager.send_to_dashboard.assert_called_once()
        call_args = mock_ws_manager.send_to_dashboard.call_args
        assert call_args[0][0] == dis_id
        assert call_args[0][1] == "disruption_created"

        # Passenger notifications: disruption_notification + options_ready
        assert mock_ws_manager.send_to_passenger.call_count == 2
        pax_calls = mock_ws_manager.send_to_passenger.call_args_list
        assert pax_calls[0][0][1] == "disruption_notification"
        assert pax_calls[1][0][1] == "options_ready"

    async def test_gate_change_no_options(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Gate change to B42",
            "status_code": "GCH",
        })

        async with session_factory() as session:
            stmt = select(OptionRow).where(OptionRow.passenger_id == "pax-001")
            options = (await session.execute(stmt)).scalars().all()
            assert len(options) == 0  # Gate changes don't generate options

    async def test_updates_passenger_status(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")

        engine = DisruptionEngine(session_factory, mock_ws_manager)
        await engine.ingest_event({
            "flight_number": "LH456",
            "origin": "MUC",
            "destination": "FRA",
            "reason": "Cancelled",
            "status_code": "CNL",
        })

        async with session_factory() as session:
            pax = await session.get(PassengerRow, "pax-001")
            assert pax.status == "notified"

    async def test_hub_disruption_multiple_flights(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_ws_manager: ConnectionManager,
    ):
        """Ingest events for two different flights creates two separate disruptions."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", destination="FRA")
            await _seed_passenger(session, "pax-002", "Bob", "LH1834", destination="CDG")

        engine = DisruptionEngine(session_factory, mock_ws_manager)

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

        async with session_factory() as session:
            d1 = await session.get(DisruptionRow, dis_id_1)
            d2 = await session.get(DisruptionRow, dis_id_2)
            assert d1.flight_number == "LH456"
            assert d2.flight_number == "LH1834"

            # Each passenger linked to their own disruption
            links_1 = (await session.execute(
                select(DisruptionPassengerRow).where(
                    DisruptionPassengerRow.disruption_id == dis_id_1,
                ),
            )).scalars().all()
            links_2 = (await session.execute(
                select(DisruptionPassengerRow).where(
                    DisruptionPassengerRow.disruption_id == dis_id_2,
                ),
            )).scalars().all()
            assert len(links_1) == 1
            assert len(links_2) == 1
            assert links_1[0].passenger_id == "pax-001"
            assert links_2[0].passenger_id == "pax-002"
