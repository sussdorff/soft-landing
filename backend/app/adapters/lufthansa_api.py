"""Adapter: LufthansaClient -> FlightDataPort.

Thin wrapper that delegates every call to the underlying LufthansaClient
and catches all exceptions so callers always get a usable (possibly empty)
result.
"""

from __future__ import annotations

import logging

from app.ports.flight_data import FlightDataPort
from app.services.lufthansa import LufthansaClient

log = logging.getLogger(__name__)


class LufthansaAPIAdapter(FlightDataPort):
    """Production adapter for the Lufthansa Open API."""

    def __init__(self, client: LufthansaClient) -> None:
        self._client = client

    async def get_schedules(
        self,
        origin: str,
        destination: str,
        date: str,
        *,
        direct_flights: bool = False,
    ) -> dict:
        try:
            return await self._client.get_schedules(
                origin, destination, date, direct_flights=direct_flights
            )
        except Exception:
            log.error("LH API error (schedules %s->%s %s)", origin, destination, date, exc_info=True)
            return {}

    async def get_lounges(
        self,
        airport_code: str,
        *,
        tier_code: str | None = None,
        cabin_class: str | None = None,
    ) -> dict:
        try:
            return await self._client.get_lounges(
                airport_code, cabin_class=cabin_class, tier_code=tier_code
            )
        except Exception:
            log.error("LH API error (lounges %s)", airport_code, exc_info=True)
            return {}

    async def get_flight_status(self, flight_number: str, date: str) -> dict:
        try:
            return await self._client.get_flight_status(flight_number, date)
        except Exception:
            log.error("LH API error (flight status %s %s)", flight_number, date, exc_info=True)
            return {}

    async def get_seat_map(
        self,
        flight_number: str,
        origin: str,
        destination: str,
        date: str,
        cabin_class: str,
    ) -> dict:
        try:
            return await self._client.get_seat_map(
                flight_number, origin, destination, date, cabin_class
            )
        except Exception:
            log.error("LH API error (seat map %s)", flight_number, exc_info=True)
            return {}

    async def get_airport_info(self, airport_code: str) -> dict:
        try:
            return await self._client.get_airport_info(airport_code)
        except Exception:
            log.error("LH API error (airport info %s)", airport_code, exc_info=True)
            return {}
