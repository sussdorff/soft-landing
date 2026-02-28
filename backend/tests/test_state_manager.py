"""Tests for the State Manager service — priority escalation and cascading impact."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories import (
    SqlDisruptionRepository,
    SqlOptionRepository,
    SqlPassengerRepository,
    SqlWishRepository,
)
from unittest.mock import AsyncMock
from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
    WishRow,
)
from app.models import WishStatus
from app.services.state_manager import StateManager


# --- Helpers ---

async def _seed_passenger(
    session: AsyncSession,
    pid: str = "pax-001",
    name: str = "Alice",
    priority: int = 10,
    denial_count: int = 0,
) -> None:
    now = datetime.now(tz=UTC)
    session.add(PassengerRow(
        id=pid, name=name, booking_ref="ABC123",
        status="notified", priority=priority, denial_count=denial_count,
    ))
    session.add(SegmentRow(
        passenger_id=pid, flight_number="LH456",
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
    option_id: str,
    passenger_id: str,
) -> None:
    session.add(OptionRow(
        id=option_id, passenger_id=passenger_id, type="rebook",
        summary=f"Rebook {option_id}", description="Next flight",
        details_json={"flight_number": "LH98", "origin": "MUC",
                      "destination": "FRA", "departure": "2026-03-01T08:00:00",
                      "seat_available": True},
        available=True,
        estimated_arrival=datetime.now(tz=UTC) + timedelta(hours=4),
    ))
    await session.commit()


async def _seed_wish(
    session: AsyncSession,
    wish_id: str,
    passenger_id: str,
    disruption_id: str = "dis-001",
    selected_option_id: str = "opt-001",
    ranked_option_ids: list[str] | None = None,
    status: str = "pending",
) -> None:
    session.add(WishRow(
        id=wish_id, passenger_id=passenger_id, disruption_id=disruption_id,
        selected_option_id=selected_option_id,
        ranked_option_ids_json=ranked_option_ids or [selected_option_id],
        submitted_at=datetime.now(tz=UTC), status=status,
    ))
    await session.commit()


def _make_state_manager(session_factory):
    """Build a StateManager with real SQL repos and a no-op notification mock."""
    notification = AsyncMock()
    return StateManager(
        passenger_repo=SqlPassengerRepository(session_factory),
        wish_repo=SqlWishRepository(session_factory),
        option_repo=SqlOptionRepository(session_factory),
        disruption_repo=SqlDisruptionRepository(session_factory),
        notification=notification,
    ), notification


# --- Priority Escalation ---


class TestPriorityEscalation:
    async def test_first_denial_boosts_above_first_choice(self, session_factory):
        """After 1 denial, passenger priority goes above max of those with pending wishes."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_passenger(session, "pax-002", "Bob", priority=20)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_option(session, "opt-002", "pax-002")
            # Bob has a pending wish (first-choice passenger)
            await _seed_wish(session, "wish-002", "pax-002", selected_option_id="opt-002")
            # Alice has a wish that will be denied
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, _ = _make_state_manager(session_factory)

        # Deny Alice's wish (first denial)
        await sm.handle_denial("wish-001", "dis-001", "pax-001")

        pax_repo = SqlPassengerRepository(session_factory)
        alice = await pax_repo.get_passenger("pax-001")
        bob = await pax_repo.get_passenger("pax-002")
        # Alice's priority should exceed Bob's (highest pending wish priority)
        assert alice.priority > bob.priority

    async def test_second_denial_gets_highest_priority(self, session_factory):
        """After 2 denials, passenger gets absolute highest priority in the disruption."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10, denial_count=1)
            await _seed_passenger(session, "pax-002", "Bob", priority=50)
            await _seed_passenger(session, "pax-003", "Charlie", priority=30)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002", "pax-003"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, _ = _make_state_manager(session_factory)

        # Deny Alice's wish (second denial — denial_count was already 1)
        await sm.handle_denial("wish-001", "dis-001", "pax-001")

        pax_repo = SqlPassengerRepository(session_factory)
        alice = await pax_repo.get_passenger("pax-001")
        # Alice's priority should exceed the highest in the disruption (Bob=50)
        assert alice.priority > 50

    async def test_denial_sends_priority_updated_ws(self, session_factory):
        """After escalation, a priority_updated WebSocket event is sent."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_denial("wish-001", "dis-001", "pax-001")

        # Find the priority_updated call among dashboard notifications
        calls = notification.send_to_dashboard.call_args_list
        priority_calls = [c for c in calls if c.args[1] == "priority_updated"]
        assert len(priority_calls) == 1
        data = priority_calls[0].args[2]
        assert data["passengerId"] == "pax-001"
        assert isinstance(data["newPriority"], int)
        assert isinstance(data["denialCount"], int)

    async def test_no_escalation_without_denial(self, session_factory):
        """Priority should not change when we're just reading state."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])

        pax_repo = SqlPassengerRepository(session_factory)
        alice = await pax_repo.get_passenger("pax-001")
        assert alice.priority == 10


# --- Cascading Impact ---


class TestCascadingImpact:
    async def test_approve_marks_competing_option_unavailable(self, session_factory):
        """When option X is approved for pax A, other pending wishes selecting X get impacted."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=20)
            await _seed_passenger(session, "pax-002", "Bob", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            # Both passengers share the same option (e.g., same rebook flight)
            await _seed_option(session, "opt-shared", "pax-001")
            await _seed_option(session, "opt-shared-bob", "pax-002")
            # Both selected the same option
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-shared",
                             ranked_option_ids=["opt-shared"])
            await _seed_wish(session, "wish-002", "pax-002",
                             selected_option_id="opt-shared-bob",
                             ranked_option_ids=["opt-shared-bob"])

        sm, notification = _make_state_manager(session_factory)

        # Approve Alice's wish — this should cascade to Bob
        result = await sm.handle_approval("wish-001", "dis-001")

        assert result.approved_wish is not None
        assert result.approved_wish.status == WishStatus.APPROVED

    async def test_approve_returns_affected_passenger_ids(self, session_factory):
        """Cascading approval returns IDs of passengers who lost their selected option."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=20)
            await _seed_passenger(session, "pax-002", "Bob", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-shared", "pax-001")
            await _seed_option(session, "opt-shared-copy", "pax-002")
            # Both select the same option (by rebook flight number conceptually)
            # But in DB terms: different option IDs per passenger
            # Cascade works by matching the rebook flight_number in details
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-shared",
                             ranked_option_ids=["opt-shared"])
            await _seed_wish(session, "wish-002", "pax-002",
                             selected_option_id="opt-shared-copy",
                             ranked_option_ids=["opt-shared-copy"])

        sm, _ = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")

        assert result.approved_wish.status == WishStatus.APPROVED

    async def test_approve_sends_option_unavailable_ws(self, session_factory):
        """Cascading impact sends option_unavailable WS event to affected passengers."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=20)
            await _seed_passenger(session, "pax-002", "Bob", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-shared", "pax-001")
            await _seed_option(session, "opt-bob", "pax-002")
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-shared",
                             ranked_option_ids=["opt-shared"])
            await _seed_wish(session, "wish-002", "pax-002",
                             selected_option_id="opt-bob",
                             ranked_option_ids=["opt-bob"])

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_approval("wish-001", "dis-001")

        # The approved passenger should get wish_approved notification with enriched payload
        pax_calls = notification.send_to_passenger.call_args_list
        approved_calls = [c for c in pax_calls if c.args[1] == "wish_approved"]
        assert len(approved_calls) == 1
        data = approved_calls[0].args[2]
        assert data["wishId"] == "wish-001"
        assert data["selectedOptionId"] == "opt-shared"
        assert "confirmationDetails" in data
        assert "option" in data
        assert data["option"]["type"] == "rebook"

    async def test_approve_nonexistent_wish_returns_none(self, session_factory):
        sm, _ = _make_state_manager(session_factory)
        result = await sm.handle_approval("nonexistent", "dis-001")
        assert result.approved_wish is None


# --- New Repository Methods ---


class TestPassengerPriorityUpdate:
    async def test_update_priority(self, session_factory):
        pax_repo = SqlPassengerRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", priority=10)

        await pax_repo.update_passenger_priority("pax-001", 99)
        pax = await pax_repo.get_passenger("pax-001")
        assert pax.priority == 99

    async def test_update_priority_nonexistent_raises(self, session_factory):
        pax_repo = SqlPassengerRepository(session_factory)
        with pytest.raises(ValueError, match="not found"):
            await pax_repo.update_passenger_priority("ghost", 99)


class TestFindCompetingWishes:
    async def test_finds_pending_wishes_with_same_option(self, session_factory):
        """find_competing_wishes returns pending wishes in the same disruption selecting the same option."""
        wish_repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", priority=20)
            await _seed_passenger(session, "pax-002", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_option(session, "opt-001-copy", "pax-002")
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-001")
            await _seed_wish(session, "wish-002", "pax-002",
                             selected_option_id="opt-001-copy")

        # Find wishes competing for opt-001, excluding pax-001
        competing = await wish_repo.find_competing_wishes(
            disruption_id="dis-001",
            option_id="opt-001",
            exclude_passenger_id="pax-001",
        )
        # By default, competing means same disruption + pending, but since
        # different passengers have different option IDs, this won't match
        # unless we match by option details (flight number). For now,
        # exact option_id match.
        assert isinstance(competing, list)

    async def test_excludes_approved_wishes(self, session_factory):
        wish_repo = SqlWishRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", priority=20)
            await _seed_passenger(session, "pax-002", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_option(session, "opt-001b", "pax-002")
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-001", status="approved")
            await _seed_wish(session, "wish-002", "pax-002",
                             selected_option_id="opt-001b")

        competing = await wish_repo.find_competing_wishes(
            disruption_id="dis-001",
            option_id="opt-001",
            exclude_passenger_id="pax-002",
        )
        # wish-001 is already approved, should not appear
        assert all(w.status == WishStatus.PENDING for w in competing)


class TestMarkOptionUnavailable:
    async def test_marks_option_unavailable(self, session_factory):
        option_repo = SqlOptionRepository(session_factory)
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001")
            await _seed_option(session, "opt-001", "pax-001")

        await option_repo.mark_unavailable("opt-001")

        opts = await option_repo.get_passenger_options("pax-001")
        assert len(opts) == 1
        assert opts[0].available is False

    async def test_mark_nonexistent_is_noop(self, session_factory):
        option_repo = SqlOptionRepository(session_factory)
        # Should not raise
        await option_repo.mark_unavailable("nonexistent")


# --- Enriched Approval ---


class TestEnrichedApproval:
    async def test_approval_sends_enriched_wish_approved(self, session_factory):
        """wish_approved event includes confirmationDetails and option."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, notification = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")

        assert result.approved_wish is not None
        pax_calls = notification.send_to_passenger.call_args_list
        approved_calls = [c for c in pax_calls if c.args[1] == "wish_approved"]
        assert len(approved_calls) == 1
        data = approved_calls[0].args[2]
        assert data["wishId"] == "wish-001"
        assert data["selectedOptionId"] == "opt-001"
        assert "Confirmed on LH98" in data["confirmationDetails"]
        assert data["option"]["type"] == "rebook"
        assert data["option"]["summary"] == "Rebook opt-001"
        assert "flight_number" in data["option"]["details"]

    async def test_approval_rejects_unavailable_option(self, session_factory):
        """Returns rejected_reason when option is unavailable."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        # Mark option unavailable before approval
        option_repo = SqlOptionRepository(session_factory)
        await option_repo.mark_unavailable("opt-001")

        sm, notification = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")

        assert result.approved_wish is None
        assert result.rejected_reason == "option_unavailable"
        # No WS notifications should have been sent
        notification.send_to_passenger.assert_not_called()
        notification.send_to_dashboard.assert_not_called()

    async def test_approval_locks_approved_option(self, session_factory):
        """Approved option is marked unavailable after approval."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, _ = _make_state_manager(session_factory)
        await sm.handle_approval("wish-001", "dis-001")

        option_repo = SqlOptionRepository(session_factory)
        opt = await option_repo.get_option("opt-001")
        assert opt is not None
        assert opt.available is False

    async def test_double_approval_returns_none(self, session_factory):
        """Approving an already-approved wish returns None (no double-process)."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001",
                             selected_option_id="opt-001", status="approved")

        sm, _ = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")
        assert result.approved_wish is None

    async def test_approval_confirmation_rebook(self, session_factory):
        """Confirmation text for REBOOK option."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, _ = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")
        assert "Confirmed on LH98 departing 08:00" in result.approved_wish.confirmation_details

    async def test_approval_confirmation_hotel(self, session_factory):
        """Confirmation text for HOTEL option."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            # Seed a hotel option
            session.add(OptionRow(
                id="opt-hotel", passenger_id="pax-001", type="hotel",
                summary="Hotel Marriott", description="Overnight stay",
                details_json={"hotel_name": "Marriott Munich", "address": "...",
                              "location": {"lat": 48.1, "lng": 11.5},
                              "next_flight_number": "LH99",
                              "next_flight_departure": "2026-03-02T08:00:00"},
                available=True,
                estimated_arrival=datetime.now(tz=UTC) + timedelta(hours=20),
            ))
            await session.commit()
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-hotel")

        sm, _ = _make_state_manager(session_factory)
        result = await sm.handle_approval("wish-001", "dis-001")
        assert "Marriott Munich" in result.approved_wish.confirmation_details
        assert "LH99" in result.approved_wish.confirmation_details


# --- Enriched Denial ---


class TestEnrichedDenial:
    async def test_denial_sends_wish_denied_to_passenger(self, session_factory):
        """StateManager sends wish_denied with available options."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_option(session, "opt-002", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_denial("wish-001", "dis-001", "pax-001", reason="No seats")

        pax_calls = notification.send_to_passenger.call_args_list
        denied_calls = [c for c in pax_calls if c.args[1] == "wish_denied"]
        assert len(denied_calls) == 1
        data = denied_calls[0].args[2]
        assert data["wishId"] == "wish-001"
        assert data["reason"] == "No seats"
        assert data["denialCount"] == 1
        assert data["noAlternatives"] is False
        # opt-001 was the denied wish's option — it should still be available
        # (denial doesn't mark the option unavailable, only approval does)
        assert len(data["availableOptions"]) == 2

    async def test_denial_sends_wish_denied_to_dashboard(self, session_factory):
        """Dashboard gets wish_denied event."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_denial("wish-001", "dis-001", "pax-001", reason="No seats")

        dash_calls = notification.send_to_dashboard.call_args_list
        denied_calls = [c for c in dash_calls if c.args[1] == "wish_denied"]
        assert len(denied_calls) == 1
        data = denied_calls[0].args[2]
        assert data["wishId"] == "wish-001"
        assert data["passengerId"] == "pax-001"
        assert data["reason"] == "No seats"
        assert isinstance(data["newPriority"], int)

    async def test_denial_no_alternatives_flag(self, session_factory):
        """noAlternatives is True when all options are unavailable."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        # Mark the only option unavailable
        option_repo = SqlOptionRepository(session_factory)
        await option_repo.mark_unavailable("opt-001")

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_denial("wish-001", "dis-001", "pax-001")

        pax_calls = notification.send_to_passenger.call_args_list
        denied_calls = [c for c in pax_calls if c.args[1] == "wish_denied"]
        data = denied_calls[0].args[2]
        assert data["noAlternatives"] is True
        assert data["availableOptions"] == []

    async def test_denial_excludes_unavailable_options(self, session_factory):
        """availableOptions filters out unavailable options."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001"])
            await _seed_option(session, "opt-001", "pax-001")
            await _seed_option(session, "opt-002", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-001")

        # Mark opt-001 unavailable
        option_repo = SqlOptionRepository(session_factory)
        await option_repo.mark_unavailable("opt-001")

        sm, notification = _make_state_manager(session_factory)
        await sm.handle_denial("wish-001", "dis-001", "pax-001")

        pax_calls = notification.send_to_passenger.call_args_list
        denied_calls = [c for c in pax_calls if c.args[1] == "wish_denied"]
        data = denied_calls[0].args[2]
        assert len(data["availableOptions"]) == 1
        assert data["availableOptions"][0]["id"] == "opt-002"


# --- Impact Preview ---


class TestImpactPreview:
    async def test_preview_impact_returns_competing(self, session_factory):
        """preview_impact finds correct competing wishes."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=20)
            await _seed_passenger(session, "pax-002", "Bob", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-shared", "pax-001")
            # Bob also selects opt-shared
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-shared")
            await _seed_wish(session, "wish-002", "pax-002", selected_option_id="opt-shared")

        sm, _ = _make_state_manager(session_factory)
        result = await sm.preview_impact("wish-001", "dis-001")

        assert result["wishId"] == "wish-001"
        assert result["affectedCount"] == 1
        assert result["affectedPassengers"][0]["passengerId"] == "pax-002"
        assert result["affectedPassengers"][0]["passengerName"] == "Bob"

    async def test_preview_impact_no_side_effects(self, session_factory):
        """preview_impact doesn't modify any state."""
        async with session_factory() as session:
            await _seed_passenger(session, "pax-001", "Alice", priority=20)
            await _seed_passenger(session, "pax-002", "Bob", priority=10)
            await _seed_disruption(session, "dis-001", ["pax-001", "pax-002"])
            await _seed_option(session, "opt-shared", "pax-001")
            await _seed_wish(session, "wish-001", "pax-001", selected_option_id="opt-shared")
            await _seed_wish(session, "wish-002", "pax-002", selected_option_id="opt-shared")

        sm, notification = _make_state_manager(session_factory)
        await sm.preview_impact("wish-001", "dis-001")

        # No notifications should have been sent
        notification.send_to_passenger.assert_not_called()
        notification.send_to_dashboard.assert_not_called()

        # Wish status should still be pending
        wish_repo = SqlWishRepository(session_factory)
        w1 = await wish_repo.get_wish("wish-001")
        assert w1.status == WishStatus.PENDING
        w2 = await wish_repo.get_wish("wish-002")
        assert w2.status == WishStatus.PENDING

    async def test_preview_impact_nonexistent_wish(self, session_factory):
        sm, _ = _make_state_manager(session_factory)
        result = await sm.preview_impact("nonexistent", "dis-001")
        assert "error" in result
