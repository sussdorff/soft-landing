"""State Manager — priority escalation and cascading impact on approve/deny.

Orchestrates the business rules:
- Priority escalation: 1 denial → above first-choice passengers,
  2+ denials → highest priority in the disruption.
- Cascading impact: when approving option X for passenger A, mark option X
  as unavailable for all other passengers who selected it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Wish, WishStatus
from app.ports.notification import NotificationPort
from app.ports.repositories import (
    DisruptionRepository,
    OptionRepository,
    PassengerRepository,
    WishRepository,
)


@dataclass
class ApprovalResult:
    """Result of handling an approval, including cascading impacts."""
    approved_wish: Wish | None
    affected_passenger_ids: list[str] = field(default_factory=list)


class StateManager:
    """Manages passenger state transitions with priority escalation and cascading impact."""

    def __init__(
        self,
        passenger_repo: PassengerRepository,
        wish_repo: WishRepository,
        option_repo: OptionRepository,
        disruption_repo: DisruptionRepository,
        notification: NotificationPort,
    ) -> None:
        self._passengers = passenger_repo
        self._wishes = wish_repo
        self._options = option_repo
        self._disruptions = disruption_repo
        self._notification = notification

    async def handle_denial(
        self,
        wish_id: str,
        disruption_id: str,
        passenger_id: str,
        reason: str = "Denied by gate agent",
    ) -> Wish | None:
        """Deny a wish and escalate passenger priority.

        Priority rules:
        - 1st denial: priority = max(pending wish priorities in disruption) + 1
        - 2nd+ denial: priority = max(all priorities in disruption) + 1
        """
        wish = await self._wishes.deny_wish(wish_id, reason)
        if not wish:
            return None

        # Fetch the updated passenger to read new denial_count
        pax = await self._passengers.get_passenger(passenger_id)
        if not pax:
            return wish

        new_priority = await self._compute_escalated_priority(
            disruption_id, passenger_id, pax.denial_count,
        )
        await self._passengers.update_passenger_priority(passenger_id, new_priority)

        await self._notification.send_to_dashboard(disruption_id, "priority_updated", {
            "passengerId": passenger_id,
            "newPriority": new_priority,
            "denialCount": pax.denial_count,
        })

        return wish

    async def handle_approval(
        self,
        wish_id: str,
        disruption_id: str,
    ) -> ApprovalResult:
        """Approve a wish and compute cascading impact.

        Returns the approved wish plus a list of passenger IDs whose
        selected option became unavailable.
        """
        wish = await self._wishes.approve_wish(wish_id)
        if not wish:
            return ApprovalResult(approved_wish=None)

        # Notify the approved passenger
        await self._notification.send_to_passenger(wish.passenger_id, "wish_approved", {
            "wishId": wish.id,
            "selectedOptionId": wish.selected_option_id,
        })

        # Find competing wishes in the same disruption for the same option
        competing = await self._wishes.find_competing_wishes(
            disruption_id=disruption_id,
            option_id=wish.selected_option_id,
            exclude_passenger_id=wish.passenger_id,
        )

        affected_ids: list[str] = []
        for comp_wish in competing:
            # Mark their selected option as unavailable
            await self._options.mark_unavailable(comp_wish.selected_option_id)
            affected_ids.append(comp_wish.passenger_id)

            # Notify affected passenger
            await self._notification.send_to_passenger(
                comp_wish.passenger_id, "option_unavailable", {
                    "optionId": comp_wish.selected_option_id,
                    "reason": "Selected by another passenger",
                },
            )

            # Notify dashboard
            await self._notification.send_to_dashboard(
                disruption_id, "option_unavailable", {
                    "optionId": comp_wish.selected_option_id,
                    "affectedPassengerId": comp_wish.passenger_id,
                },
            )

        # Notify dashboard about the approval
        await self._notification.send_to_dashboard(disruption_id, "wish_approved", {
            "wishId": wish.id,
            "passengerId": wish.passenger_id,
            "selectedOptionId": wish.selected_option_id,
            "affectedPassengerIds": affected_ids,
        })

        return ApprovalResult(
            approved_wish=wish,
            affected_passenger_ids=affected_ids,
        )

    async def _compute_escalated_priority(
        self,
        disruption_id: str,
        passenger_id: str,
        denial_count: int,
    ) -> int:
        """Compute the escalated priority for a denied passenger.

        - 1 denial: above max priority of passengers with pending wishes
        - 2+ denials: above max priority of all passengers in disruption
        """
        if denial_count >= 2:
            # Highest priority across ALL passengers in the disruption
            all_pax = await self._disruptions.get_disruption_passengers(disruption_id)
            max_priority = max(
                (p.priority for p in all_pax if p.id != passenger_id),
                default=0,
            )
            return max_priority + 10
        else:
            # Above max priority of passengers with pending wishes
            pending_wishes = [
                w for w in await self._wishes.list_wishes(disruption_id=disruption_id)
                if w.status == WishStatus.PENDING and w.passenger_id != passenger_id
            ]
            max_priority = 0
            for w in pending_wishes:
                pax = await self._passengers.get_passenger(w.passenger_id)
                if pax and pax.priority > max_priority:
                    max_priority = pax.priority
            return max_priority + 1 if max_priority > 0 else 1
