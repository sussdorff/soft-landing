"""Disruption Engine — event detection, classification, and orchestration.

Receives raw disruption events, classifies them, finds affected passengers,
triggers option generation, and sends WebSocket notifications.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    PassengerRow,
    SegmentRow,
)
from app.models import DisruptionType
from app.services.option_generator import OptionGenerator
from app.ws import ConnectionManager


# Status code → DisruptionType mapping
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


class DisruptionEngine:
    """Orchestrates disruption event processing."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ws_manager: ConnectionManager,
    ) -> None:
        self.session_factory = session_factory
        self.ws_manager = ws_manager
        self.option_generator = OptionGenerator()

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

    @staticmethod
    async def find_affected_passengers(
        session: AsyncSession, flight_number: str,
    ) -> list[PassengerRow]:
        """Find all passengers who have a segment on the given flight."""
        stmt = (
            select(PassengerRow)
            .join(SegmentRow)
            .where(SegmentRow.flight_number == flight_number)
            .options(selectinload(PassengerRow.segments))
        )
        rows = (await session.execute(stmt)).scalars().unique().all()
        return list(rows)

    async def ingest_event(self, raw: dict) -> str:
        """Orchestrate full disruption processing.

        1. Classify event
        2. Create disruption record
        3. Find affected passengers
        4. Link passengers to disruption
        5. Generate options for each passenger
        6. Send WebSocket notifications

        Returns the disruption ID.
        """
        dtype = self.classify_event(raw)
        disruption_id = uuid4().hex[:8]
        now = datetime.now(tz=UTC)

        async with self.session_factory() as session:
            # Create disruption row
            disruption = DisruptionRow(
                id=disruption_id,
                type=dtype.value,
                flight_number=raw["flight_number"],
                origin=raw.get("origin", ""),
                destination=raw.get("destination", ""),
                reason=raw.get("reason", ""),
                explanation=raw.get("explanation", ""),
                detected_at=now,
            )
            session.add(disruption)

            # Find affected passengers
            passengers = await self.find_affected_passengers(
                session, raw["flight_number"],
            )

            # Link passengers + update status + generate options
            for pax in passengers:
                session.add(DisruptionPassengerRow(
                    disruption_id=disruption_id,
                    passenger_id=pax.id,
                ))
                pax.status = "notified"

                # Generate options
                self.option_generator.generate_options(
                    session,
                    disruption_id=disruption_id,
                    passenger_id=pax.id,
                    disruption_type=dtype,
                    destination=raw.get("destination", ""),
                    base_time=now,
                )

            await session.commit()

        # Send WebSocket notifications (outside the DB session)
        await self.ws_manager.send_to_dashboard(disruption_id, "disruption_created", {
            "disruptionId": disruption_id,
            "type": dtype.value,
            "flightNumber": raw["flight_number"],
            "affectedPassengers": len(passengers),
        })

        for pax in passengers:
            await self.ws_manager.send_to_passenger(
                pax.id, "disruption_notification", {
                    "disruptionId": disruption_id,
                    "type": dtype.value,
                    "flightNumber": raw["flight_number"],
                    "reason": raw.get("reason", ""),
                },
            )
            await self.ws_manager.send_to_passenger(
                pax.id, "options_ready", {
                    "disruptionId": disruption_id,
                    "passengerId": pax.id,
                },
            )

        return disruption_id
