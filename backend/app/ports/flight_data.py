"""Port: Flight data access (schedules, lounges, seat maps, status).

Adapters:
  - LufthansaAPIAdapter: live data from Lufthansa Open API
  - StaticDataAdapter: deterministic seed data for offline/demo mode

Graceful degradation:
  Adapters should return empty dicts on transient errors (network timeout,
  rate-limit) and log the failure.  Callers must tolerate empty results.
  Authentication failures should raise so the caller can surface the issue.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class FlightDataPort(ABC):
    """Contract for querying flight operations data."""

    @abstractmethod
    async def get_schedules(
        self,
        origin: str,
        destination: str,
        date: str,
        *,
        direct_flights: bool = False,
    ) -> dict:
        """Return available flight schedules between two airports.

        Args:
            origin: 3-letter IATA airport code (e.g. "MUC").
            destination: 3-letter IATA airport code (e.g. "FRA").
            date: Departure date, ISO format yyyy-MM-dd or yyyy-MM-ddTHH:mm.
            direct_flights: If True, only return non-stop flights.

        Returns:
            Parsed schedule resource.  Empty dict on failure.
        """

    @abstractmethod
    async def get_lounges(
        self,
        airport_code: str,
        *,
        tier_code: str | None = None,
        cabin_class: str | None = None,
    ) -> dict:
        """Return lounge information for an airport.

        Args:
            airport_code: 3-letter IATA code (e.g. "FRA").
            tier_code: Loyalty tier filter — HON, SEN, FTL, or SGC.
                       Mutually exclusive with cabin_class.
            cabin_class: Cabin class filter — F, C, E, or M.
                         Mutually exclusive with tier_code.

        Returns:
            Parsed lounge resource.  Empty dict on failure.
        """

    @abstractmethod
    async def get_flight_status(
        self,
        flight_number: str,
        date: str,
    ) -> dict:
        """Return operational status for a specific flight.

        Args:
            flight_number: IATA carrier + number (e.g. "LH400").
            date: Departure date in yyyy-MM-dd format.

        Returns:
            Parsed flight-status resource.  Empty dict on failure.
        """

    @abstractmethod
    async def get_seat_map(
        self,
        flight_number: str,
        origin: str,
        destination: str,
        date: str,
        cabin_class: str,
    ) -> dict:
        """Return seat availability for a flight.

        Args:
            flight_number: IATA carrier + number (e.g. "LH400").
            origin: 3-letter IATA origin code.
            destination: 3-letter IATA destination code.
            date: Departure date in yyyy-MM-dd format.
            cabin_class: IATA cabin code (F/C/M/Y).

        Returns:
            Parsed seat-map resource.  Empty dict on failure.
        """

    @abstractmethod
    async def get_nearest_airports(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """Return nearest airports for a geographic position.

        Args:
            latitude: Latitude (-90 to +90).
            longitude: Longitude (-180 to +180).

        Returns:
            Parsed nearest-airport resource.  Empty dict on failure.
        """

    @abstractmethod
    async def get_airport_info(self, airport_code: str) -> dict:
        """Return airport reference data.

        Args:
            airport_code: 3-letter IATA code.

        Returns:
            Parsed airport resource.  Empty dict on failure.
        """
