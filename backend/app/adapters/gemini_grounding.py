"""Adapter: Gemini grounding via Google Search + Maps.

Wraps :class:`GeminiGroundingService` behind the :class:`GroundingPort`
interface.  Handles the case where the service is *None* (missing API key)
by returning safe defaults — empty lists, generic fallback strings, or an
empty :class:`FlightContext`.
"""

from __future__ import annotations

import logging

from app.ports.grounding import GroundingPort
from app.services.gemini import (
    FlightContext,
    GeminiGroundingService,
    HotelOption,
    TransportOption,
)

log = logging.getLogger(__name__)

_FALLBACK_EXPLANATION = (
    "A disruption has affected your flight. "
    "We are working to provide you with alternatives as quickly as possible."
)


class GeminiGroundingAdapter(GroundingPort):
    """Production adapter delegating to Gemini with graceful degradation."""

    def __init__(self, service: GeminiGroundingService | None) -> None:
        self._service = service

    # -- GroundingPort implementation --

    async def find_nearby_hotels(
        self,
        airport_code: str,
        max_results: int = 5,
    ) -> list[HotelOption]:
        if not self._service:
            log.warning("Gemini service unavailable, hotel search skipped")
            return []
        try:
            return await self._service.find_nearby_hotels(airport_code, max_results)
        except Exception:
            log.exception("Gemini error (find_nearby_hotels)")
            return []

    async def find_ground_transport(
        self,
        origin_airport: str,
        destination: str,
    ) -> list[TransportOption]:
        if not self._service:
            log.warning("Gemini service unavailable, transport search skipped")
            return []
        try:
            return await self._service.find_ground_transport(origin_airport, destination)
        except Exception:
            log.exception("Gemini error (find_ground_transport)")
            return []

    async def explain_disruption(
        self,
        disruption_type: str,
        flight_number: str,
        origin: str,
        destination: str,
        raw_reason: str,
    ) -> str:
        if not self._service:
            log.warning("Gemini service unavailable, using fallback explanation")
            return _FALLBACK_EXPLANATION
        try:
            return await self._service.explain_disruption(
                disruption_type, flight_number, origin, destination, raw_reason,
            )
        except Exception:
            log.exception("Gemini error (explain_disruption)")
            return _FALLBACK_EXPLANATION

    async def get_flight_context(
        self,
        flight_number: str,
        date: str,
    ) -> FlightContext:
        if not self._service:
            log.warning("Gemini service unavailable, returning empty flight context")
            return FlightContext()
        try:
            return await self._service.get_flight_context(flight_number, date)
        except Exception:
            log.exception("Gemini error (get_flight_context)")
            return FlightContext()

    async def describe_option(
        self,
        option_type: str,
        details: dict[str, str],
    ) -> str:
        fallback = f"Option: {option_type}. " + ", ".join(
            f"{k}: {v}" for k, v in details.items()
        )
        if not self._service:
            log.warning("Gemini service unavailable, using terse option description")
            return fallback
        try:
            return await self._service.describe_option(option_type, details)
        except Exception:
            log.exception("Gemini error (describe_option)")
            return fallback
