"""Disruption Engine — event detection, classification, and orchestration.

Receives raw disruption events, classifies them, finds affected passengers,
triggers option generation, and sends notifications via injected ports.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.models import BookingClass, DisruptionType, LoyaltyTier, Passenger
from app.ports.grounding import GroundingPort
from app.ports.notification import NotificationPort
from app.ports.repositories import DisruptionRepository

log = logging.getLogger(__name__)

# Status code -> DisruptionType mapping
_STATUS_MAP: dict[str, DisruptionType] = {
    "CNL": DisruptionType.CANCELLATION,
    "DVT": DisruptionType.DIVERSION,
    "DLY": DisruptionType.DELAY,
    "GCH": DisruptionType.GATE_CHANGE,
}

# Keyword patterns in reason text (fallback when status_code is missing)
_KEYWORD_MAP: list[tuple[list[str], DisruptionType]] = [
    (["cancel", "cancelled", "cancellation"], DisruptionType.CANCELLATION),
    (["divert", "diversion", "diverted"], DisruptionType.DIVERSION),
    (["gate change", "gate reassign", "new gate"], DisruptionType.GATE_CHANGE),
    (["delay", "delayed", "late"], DisruptionType.DELAY),
]


class OptionGeneratorPort(Protocol):
    """Minimal contract for option generation used by the engine.

    The current OptionGenerator satisfies this once Task #6 refactors it
    to drop the session parameter.
    """

    async def generate_options(
        self,
        disruption_id: str,
        passenger_id: str,
        disruption_type: DisruptionType,
        destination: str,
        *,
        loyalty_tier: LoyaltyTier = LoyaltyTier.NONE,
        booking_class: BookingClass = BookingClass.Y,
    ) -> list[str]: ...


class DisruptionEngine:
    """Orchestrates disruption event processing."""

    def __init__(
        self,
        disruption_repo: DisruptionRepository,
        grounding: GroundingPort,
        option_generator: OptionGeneratorPort,
        notification: NotificationPort,
    ) -> None:
        self._disruption_repo = disruption_repo
        self._grounding = grounding
        self._option_generator = option_generator
        self._notification = notification

    @staticmethod
    def classify_event(raw: dict) -> DisruptionType:
        """Classify a raw event dict into a DisruptionType.

        Uses status_code first, falls back to keyword matching on reason.
        Defaults to DELAY if nothing matches.
        """
        code = raw.get("status_code", "").upper().strip()
        if code in _STATUS_MAP:
            return _STATUS_MAP[code]

        reason = raw.get("reason", "").lower()
        for keywords, dtype in _KEYWORD_MAP:
            if any(kw in reason for kw in keywords):
                return dtype

        return DisruptionType.DELAY

    async def ingest_event(self, raw: dict) -> str:
        """Orchestrate full disruption processing.

        1. Classify event
        2. Find affected passengers
        3. Generate explanation via grounding
        4. Create disruption record (links passengers, sets status)
        5. Generate options for each passenger
        6. Send notifications

        Returns the disruption ID.
        """
        dtype = self.classify_event(raw)
        flight_number = raw["flight_number"]
        origin = raw.get("origin", "")
        destination = raw.get("destination", "")

        # Find affected passengers (before creating the disruption)
        passengers = await self._disruption_repo.find_affected_passengers(
            flight_number,
        )

        # Generate explanation via grounding port (graceful fallback)
        explanation = await self._grounding.explain_disruption(
            dtype.value,
            flight_number,
            origin,
            destination,
            raw.get("reason", ""),
        )

        # Create disruption + link passengers + set status to NOTIFIED
        disruption_id = await self._disruption_repo.create_disruption(
            disruption_type=dtype,
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            reason=raw.get("reason", ""),
            explanation=explanation,
            affected_passenger_ids=[p.id for p in passengers],
        )

        # Generate options for each passenger
        for pax in passengers:
            await self._option_generator.generate_options(
                disruption_id,
                pax.id,
                dtype,
                destination,
                loyalty_tier=pax.loyalty_tier,
                booking_class=pax.booking_class,
            )

        # Send notifications (fire-and-forget via port)
        await self._notification.send_to_dashboard(
            disruption_id, "disruption_created", {
                "disruptionId": disruption_id,
                "type": dtype.value,
                "flightNumber": flight_number,
                "affectedPassengers": len(passengers),
            },
        )

        for pax in passengers:
            await self._notification.send_to_passenger(
                pax.id, "disruption_notification", {
                    "disruptionId": disruption_id,
                    "type": dtype.value,
                    "flightNumber": flight_number,
                    "reason": raw.get("reason", ""),
                },
            )
            await self._notification.send_to_passenger(
                pax.id, "options_ready", {
                    "disruptionId": disruption_id,
                    "passengerId": pax.id,
                },
            )

        return disruption_id
