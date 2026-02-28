"""Ahead-of-Flight Context Engine.

Scans upcoming flights and produces pre-flight intelligence briefings
combining Gemini Search grounding context with passenger risk data.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tables import PassengerRow, SegmentRow
from app.models import FlightBriefing, LoyaltyTier
from app.ports.grounding import GroundingPort

log = logging.getLogger(__name__)

_VIP_TIERS = {LoyaltyTier.HON_CIRCLE, LoyaltyTier.SENATOR}


class AheadOfFlightEngine:
    """Produces ahead-of-flight briefings for gate agents."""

    def __init__(
        self,
        grounding: GroundingPort,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._grounding = grounding
        self._session_factory = session_factory

    async def scan_upcoming_flights(
        self, hours_ahead: int = 6,
    ) -> list[FlightBriefing]:
        """Scan flights departing within *hours_ahead* and build briefings."""
        now = datetime.now(tz=UTC)
        cutoff = now + timedelta(hours=hours_ahead)

        flights = await self._get_upcoming_flights(now, cutoff)
        if not flights:
            return []

        briefings: list[FlightBriefing] = []
        for flight_key, info in flights.items():
            flight_number, date_str = flight_key
            ctx = await self._grounding.get_flight_context(flight_number, date_str)

            risk = _compute_risk(
                weather_origin=ctx.weather_origin,
                weather_destination=ctx.weather_destination,
                disruption_info=ctx.disruption_info,
                vip_count=info["vip_count"],
                passenger_count=info["passenger_count"],
            )

            briefings.append(FlightBriefing(
                flight_number=flight_number,
                origin=info["origin"],
                destination=info["destination"],
                departure=info["departure"],
                weather_origin=ctx.weather_origin,
                weather_destination=ctx.weather_destination,
                disruption_info=ctx.disruption_info,
                airport_status=ctx.airport_status,
                relevant_events=ctx.relevant_events,
                sources=ctx.sources,
                passenger_count=info["passenger_count"],
                vip_count=info["vip_count"],
                connection_count=info["connection_count"],
                risk_level=risk,
            ))

        # Sort: high risk first, then by departure
        _risk_order = {"high": 0, "medium": 1, "low": 2}
        briefings.sort(key=lambda b: (_risk_order.get(b.risk_level, 2), b.departure))
        return briefings

    async def get_flight_briefing(
        self, flight_number: str, date: str,
    ) -> FlightBriefing | None:
        """Build a briefing for a single flight on a given date."""
        info = await self._get_flight_info(flight_number, date)
        if not info:
            return None

        ctx = await self._grounding.get_flight_context(flight_number, date)

        risk = _compute_risk(
            weather_origin=ctx.weather_origin,
            weather_destination=ctx.weather_destination,
            disruption_info=ctx.disruption_info,
            vip_count=info["vip_count"],
            passenger_count=info["passenger_count"],
        )

        return FlightBriefing(
            flight_number=flight_number,
            origin=info["origin"],
            destination=info["destination"],
            departure=info["departure"],
            weather_origin=ctx.weather_origin,
            weather_destination=ctx.weather_destination,
            disruption_info=ctx.disruption_info,
            airport_status=ctx.airport_status,
            relevant_events=ctx.relevant_events,
            sources=ctx.sources,
            passenger_count=info["passenger_count"],
            vip_count=info["vip_count"],
            connection_count=info["connection_count"],
            risk_level=risk,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_upcoming_flights(
        self, start: datetime, end: datetime,
    ) -> dict[tuple[str, str], dict]:
        """Query segments departing in [start, end], grouped by flight."""
        async with self._session_factory() as session:
            stmt = (
                select(SegmentRow, PassengerRow)
                .join(PassengerRow, SegmentRow.passenger_id == PassengerRow.id)
                .where(SegmentRow.departure >= start, SegmentRow.departure <= end)
                .order_by(SegmentRow.departure)
            )
            rows = (await session.execute(stmt)).all()

            if not rows:
                return {}

            # Count total segments per passenger (all segments, not just in window)
            # to detect connecting passengers
            pax_ids = list({pax_row.id for _, pax_row in rows})
            seg_count_stmt = select(SegmentRow.passenger_id).where(
                SegmentRow.passenger_id.in_(pax_ids),
            )
            seg_count_rows = (await session.execute(seg_count_stmt)).all()
            pax_total_segments: dict[str, int] = defaultdict(int)
            for (pid,) in seg_count_rows:
                pax_total_segments[pid] += 1

            flights: dict[tuple[str, str], dict] = {}

            for seg_row, pax_row in rows:
                date_str = seg_row.departure.strftime("%Y-%m-%d")
                key = (seg_row.flight_number, date_str)

                if key not in flights:
                    flights[key] = {
                        "origin": seg_row.origin,
                        "destination": seg_row.destination,
                        "departure": seg_row.departure,
                        "passenger_count": 0,
                        "vip_count": 0,
                        "connection_count": 0,
                        "seen_pax": set(),
                    }

                info = flights[key]
                if pax_row.id in info["seen_pax"]:
                    continue
                info["seen_pax"].add(pax_row.id)
                info["passenger_count"] += 1

                loyalty = LoyaltyTier(pax_row.loyalty_tier) if pax_row.loyalty_tier else LoyaltyTier.NONE
                if loyalty in _VIP_TIERS:
                    info["vip_count"] += 1

                if pax_total_segments[pax_row.id] > 1:
                    info["connection_count"] += 1

            # Remove internal tracking field
            for info in flights.values():
                del info["seen_pax"]

            return flights

    async def _get_flight_info(
        self, flight_number: str, date: str,
    ) -> dict | None:
        """Get passenger stats for a specific flight on a date."""
        async with self._session_factory() as session:
            stmt = (
                select(SegmentRow, PassengerRow)
                .join(PassengerRow, SegmentRow.passenger_id == PassengerRow.id)
                .where(SegmentRow.flight_number == flight_number)
            )
            rows = (await session.execute(stmt)).all()

            if not rows:
                return None

            # Count segments per passenger to detect connections
            pax_segments: dict[str, int] = defaultdict(int)
            for seg_row, pax_row in rows:
                # Count all segments for this passenger (not just this flight)
                pass

            # Need a second query for full segment count
            pax_ids = list({pax_row.id for _, pax_row in rows})
            seg_count_stmt = (
                select(SegmentRow.passenger_id)
                .where(SegmentRow.passenger_id.in_(pax_ids))
            )
            seg_rows = (await session.execute(seg_count_stmt)).all()
            for (pid,) in seg_rows:
                pax_segments[pid] += 1

            info = {
                "origin": rows[0][0].origin,
                "destination": rows[0][0].destination,
                "departure": rows[0][0].departure,
                "passenger_count": 0,
                "vip_count": 0,
                "connection_count": 0,
            }

            seen: set[str] = set()
            for seg_row, pax_row in rows:
                if pax_row.id in seen:
                    continue
                seen.add(pax_row.id)
                info["passenger_count"] += 1

                loyalty = LoyaltyTier(pax_row.loyalty_tier) if pax_row.loyalty_tier else LoyaltyTier.NONE
                if loyalty in _VIP_TIERS:
                    info["vip_count"] += 1

                if pax_segments.get(pax_row.id, 0) > 1:
                    info["connection_count"] += 1

            return info


def _compute_risk(
    *,
    weather_origin: str,
    weather_destination: str,
    disruption_info: str,
    vip_count: int,
    passenger_count: int,
) -> str:
    """Derive risk level from context signals.

    High: disruption_info mentions active issues, or weather contains severe keywords.
    Medium: weather mentions moderate issues, or high VIP ratio.
    Low: otherwise.
    """
    weather_text = f"{weather_origin} {weather_destination}".lower()
    disruption_text = disruption_info.lower()

    severe_keywords = {"storm", "blizzard", "hurricane", "typhoon", "snow", "ice",
                       "fog", "cancelled", "strike", "closed", "grounded"}
    moderate_keywords = {"delay", "wind", "rain", "thunderstorm", "warning",
                         "reduced", "construction"}

    if any(kw in disruption_text for kw in severe_keywords):
        return "high"
    if any(kw in weather_text for kw in severe_keywords):
        return "high"

    if any(kw in disruption_text for kw in moderate_keywords):
        return "medium"
    if any(kw in weather_text for kw in moderate_keywords):
        return "medium"
    if passenger_count > 0 and vip_count / passenger_count > 0.2:
        return "medium"

    return "low"
