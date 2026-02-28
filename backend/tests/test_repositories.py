"""Tests for SQL repository adapters — CRUD smoke tests against in-memory SQLite."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.repositories import (
    SqlDisruptionRepository,
    SqlOptionRepository,
    SqlPassengerRepository,
    SqlWishRepository,
)
from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
    WishRow,
)
from app.models import (
    DisruptionType,
    OptionType,
    PassengerStatus,
    RebookDetails,
    WishStatus,
)


# --- Helpers ---

async def _seed_passenger(
    session: AsyncSession,
    pid: str = "pax-001",
    name: str = "Alice",
    flight_number: str = "LH456",
    priority: int = 1,
) -> None:
    """Seed a passenger with a segment."""
    now = datetime.now(tz=UTC)
    session.add(PassengerRow(
        id=pid, name=name, booking_ref="ABC123",
        status="unaffected", priority=priority,
    ))
    session.add(SegmentRow(
        passenger_id=pid, flight_number=flight_number,
        origin="MUC", destination="FRA",
        departure=now + timedelta(hours=2),
        arrival=now + timedelta(hours=3),
        position=0,
    ))
    await session.commit()


async def _seed_disruption(
    session: AsyncSession,
    disruption_id: str = "dis-001",
    passenger_ids: list[str] | None = None,
) -> None:
    """Seed a disruption and optionally link passengers."""
    now = datetime.now(tz=UTC)
    session.add(DisruptionRow(
        id=disruption_id, type="cancellation", flight_number="LH456",
        origin="MUC", destination="FRA", reason="Snow",
        explanation="Flight cancelled", detected_at=now,
    ))
    for pid in (passenger_ids or []):
        session.add(DisruptionPassengerRow(
            disruption_id=disruption_id, passenger_id=pid,
        ))
    await session.commit()


async def _seed_option(
    session: AsyncSession,
    option_id: str = "opt-001",
    passenger_id: str = "pax-001",
) -> None:
    """Seed an option row."""
    session.add(OptionRow(
        id=option_id, passenger_id=passenger_id, type="rebook",
        summary="Rebook LH98", description="Next flight",
        details_json={"flight_number": "LH98", "origin": "MUC",
                      "destination": "FRA", "departure": "2026-03-01T08:00:00",
                      "seat_available": True},
        available=True,
        estimated_arrival=datetime.now(tz=UTC) + timedelta(hours=4),
    ))
    await session.commit()


async def _seed_wish(
    session: AsyncSession,
    wish_id: str = "wish-001",
    passenger_id: str = "pax-001",
    disruption_id: str = "dis-001",
) -> None:
    """Seed a wish row."""
    session.add(WishRow(
        id=wish_id, passenger_id=passenger_id, disruption_id=disruption_id,
        selected_option_id="opt-001", ranked_option_ids_json=["opt-001"],
        submitted_at=datetime.now(tz=UTC), status="pending",
    ))
    await session.commit()


# --- DisruptionRepository ---


class TestSqlDisruptionRepository:
    async def test_create_and_get_disruption(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)

        # Seed a passenger first (needed for linking)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")

        dis_id = await repo.create_disruption(
            disruption_type=DisruptionType.CANCELLATION,
            flight_number="LH456",
            origin="MUC",
            destination="FRA",
            reason="Snow",
            explanation="Cancelled due to heavy snow",
            affected_passenger_ids=["pax-001"],
        )

        dis = await repo.get_disruption(dis_id)
        assert dis is not None
        assert dis.type == DisruptionType.CANCELLATION
        assert dis.flight_number == "LH456"
        assert "pax-001" in dis.affected_passenger_ids

    async def test_get_nonexistent_returns_none(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        assert await repo.get_disruption("nonexistent") is None

    async def test_find_affected_passengers(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", "LH456", priority=2)
            await _seed_passenger(session, "pax-002", "Bob", "LH456", priority=1)
            await _seed_passenger(session, "pax-003", "Charlie", "LH999")

        pax = await repo.find_affected_passengers("LH456")
        assert len(pax) == 2
        # Sorted by priority desc, then name
        assert pax[0].name == "Alice"  # priority=2
        assert pax[1].name == "Bob"  # priority=1

    async def test_get_disruption_passengers(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_passenger(session, "pax-002", "Bob")
            await _seed_disruption(session, "dis-001", ["pax-001"])

        pax = await repo.get_disruption_passengers("dis-001")
        assert len(pax) == 1
        assert pax[0].id == "pax-001"

    async def test_is_empty_true(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        assert await repo.is_empty() is True

    async def test_is_empty_false(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_disruption(session)
        assert await repo.is_empty() is False

    async def test_create_disruption_sets_passenger_status(self, session_factory):
        repo = SqlDisruptionRepository(session_factory)
        pax_repo = SqlPassengerRepository(session_factory)

        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")

        await repo.create_disruption(
            disruption_type=DisruptionType.CANCELLATION,
            flight_number="LH456",
            origin="MUC",
            destination="FRA",
            reason="Snow",
            explanation="Cancelled",
            affected_passenger_ids=["pax-001"],
        )

        pax = await pax_repo.get_passenger("pax-001")
        assert pax is not None
        assert pax.status == PassengerStatus.NOTIFIED


# --- PassengerRepository ---


class TestSqlPassengerRepository:
    async def test_get_passenger(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice")

        pax = await repo.get_passenger("pax-001")
        assert pax is not None
        assert pax.name == "Alice"
        assert len(pax.original_itinerary) == 1

    async def test_get_nonexistent_returns_none(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        assert await repo.get_passenger("ghost") is None

    async def test_get_passenger_disruptions(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])

        disruptions = await repo.get_passenger_disruptions("pax-001")
        assert len(disruptions) == 1
        assert disruptions[0].id == "dis-001"

    async def test_update_passenger_status(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")

        await repo.update_passenger_status("pax-001", PassengerStatus.NOTIFIED)
        pax = await repo.get_passenger("pax-001")
        assert pax.status == PassengerStatus.NOTIFIED

    async def test_update_status_denied_increments_count(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")

        await repo.update_passenger_status("pax-001", PassengerStatus.DENIED)
        pax = await repo.get_passenger("pax-001")
        assert pax.denial_count == 1

        await repo.update_passenger_status("pax-001", PassengerStatus.DENIED)
        pax = await repo.get_passenger("pax-001")
        assert pax.denial_count == 2

    async def test_update_nonexistent_raises(self, session_factory):
        repo = SqlPassengerRepository(session_factory)
        with pytest.raises(ValueError, match="not found"):
            await repo.update_passenger_status("ghost", PassengerStatus.NOTIFIED)


# --- OptionRepository ---


class TestSqlOptionRepository:
    async def test_create_and_get_options(self, session_factory):
        repo = SqlOptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")

        opt_id = await repo.create_option(
            passenger_id="pax-001",
            option_type="rebook",
            summary="Rebook LH98",
            description="Next available flight tomorrow",
            details=RebookDetails(
                flight_number="LH98", origin="MUC", destination="FRA",
                departure=datetime.now(tz=UTC) + timedelta(hours=20),
            ),
            available=True,
            estimated_arrival=datetime.now(tz=UTC) + timedelta(hours=22),
        )

        assert isinstance(opt_id, str)
        assert len(opt_id) > 0

        opts = await repo.get_passenger_options("pax-001")
        assert len(opts) == 1
        assert opts[0].id == opt_id
        assert opts[0].type == OptionType.REBOOK
        assert opts[0].summary == "Rebook LH98"

    async def test_get_options_empty(self, session_factory):
        repo = SqlOptionRepository(session_factory)
        opts = await repo.get_passenger_options("pax-ghost")
        assert opts == []

    async def test_delete_options(self, session_factory):
        repo = SqlOptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_option(session, "opt-001")
            await _seed_option(session, "opt-002")

        await repo.delete_options(["opt-001"])
        remaining = await repo.get_passenger_options("pax-001")
        assert len(remaining) == 1
        assert remaining[0].id == "opt-002"

    async def test_delete_options_empty_list(self, session_factory):
        repo = SqlOptionRepository(session_factory)
        # Should not raise
        await repo.delete_options([])

    async def test_delete_nonexistent_ignored(self, session_factory):
        repo = SqlOptionRepository(session_factory)
        # Should not raise
        await repo.delete_options(["nonexistent-id"])


# --- WishRepository ---


class TestSqlWishRepository:
    async def test_create_wish_returns_wish(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")

        wish = await repo.create_wish(
            passenger_id="pax-001",
            disruption_id="dis-001",
            selected_option_id="opt-001",
            ranked_option_ids=["opt-001"],
        )

        assert wish.passenger_id == "pax-001"
        assert wish.disruption_id == "dis-001"
        assert wish.status == WishStatus.PENDING

    async def test_create_wish_sets_passenger_status_chose(self, session_factory):
        wish_repo = SqlWishRepository(session_factory)
        pax_repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")

        await wish_repo.create_wish(
            passenger_id="pax-001",
            disruption_id="dis-001",
            selected_option_id="opt-001",
            ranked_option_ids=["opt-001"],
        )

        pax = await pax_repo.get_passenger("pax-001")
        assert pax.status == PassengerStatus.CHOSE

    async def test_approve_wish(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001")

        wish = await repo.approve_wish("wish-001")
        assert wish is not None
        assert wish.status == WishStatus.APPROVED

    async def test_approve_nonexistent_returns_none(self, session_factory):
        repo = SqlWishRepository(session_factory)
        assert await repo.approve_wish("nonexistent") is None

    async def test_deny_wish(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001")

        wish = await repo.deny_wish("wish-001", "Seat unavailable")
        assert wish is not None
        assert wish.status == WishStatus.DENIED
        assert wish.denial_reason == "Seat unavailable"

    async def test_deny_wish_increments_denial_count(self, session_factory):
        repo = SqlWishRepository(session_factory)
        pax_repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001")

        await repo.deny_wish("wish-001", "No seats")
        pax = await pax_repo.get_passenger("pax-001")
        assert pax.denial_count == 1

    async def test_deny_nonexistent_returns_none(self, session_factory):
        repo = SqlWishRepository(session_factory)
        assert await repo.deny_wish("nonexistent", "reason") is None

    async def test_get_wish(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001")

        wish = await repo.get_wish("wish-001")
        assert wish is not None
        assert wish.id == "wish-001"

    async def test_get_wish_nonexistent(self, session_factory):
        repo = SqlWishRepository(session_factory)
        assert await repo.get_wish("ghost") is None

    async def test_list_wishes_all(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001")
            await _seed_wish(session, "wish-002")

        wishes = await repo.list_wishes()
        assert len(wishes) == 2

    async def test_list_wishes_filtered(self, session_factory):
        repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_disruption(session, "dis-002")
            await _seed_option(session, "opt-001")
            await _seed_wish(session, "wish-001", disruption_id="dis-001")
            await _seed_wish(session, "wish-002", disruption_id="dis-002")

        wishes = await repo.list_wishes(disruption_id="dis-001")
        assert len(wishes) == 1
        assert wishes[0].disruption_id == "dis-001"
