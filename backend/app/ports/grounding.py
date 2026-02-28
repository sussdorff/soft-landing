"""Port: AI grounding (search, maps, natural-language generation).

Adapters:
  - GeminiGroundingAdapter: Gemini with Google Search + Maps grounding
  - StaticDataAdapter: deterministic canned responses for tests/demo

Graceful degradation:
  - find_nearby_hotels / find_ground_transport: return empty list on failure.
  - explain_disruption / describe_option: return a generic fallback string.
  - get_flight_context: return a FlightContext with empty fields.
  Adapters log errors internally; callers should not need try/except.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.gemini import FlightContext, HotelOption, TransportOption


class GroundingPort(ABC):
    """Contract for AI-grounded search, maps, and text generation."""

    @abstractmethod
    async def find_nearby_hotels(
        self,
        airport_code: str,
        max_results: int = 5,
    ) -> list[HotelOption]:
        """Find hotels near an airport for stranded passengers.

        Args:
            airport_code: 3-letter IATA code.
            max_results: Cap on returned results.

        Returns:
            Hotel options sorted by proximity.  Empty list on failure.
        """

    @abstractmethod
    async def find_ground_transport(
        self,
        origin_airport: str,
        destination: str,
    ) -> list[TransportOption]:
        """Find ground transport alternatives (train, bus, taxi).

        Args:
            origin_airport: IATA code of the departure airport.
            destination: City name or airport code of the final destination.

        Returns:
            Transport options sorted by travel time.  Empty list on failure.
        """

    @abstractmethod
    async def explain_disruption(
        self,
        disruption_type: str,
        flight_number: str,
        origin: str,
        destination: str,
        raw_reason: str,
    ) -> str:
        """Generate a passenger-friendly disruption explanation.

        Args:
            disruption_type: Category string (e.g. "cancellation").
            flight_number: IATA flight number (e.g. "LH1234").
            origin: Origin airport IATA code.
            destination: Destination airport IATA code.
            raw_reason: Technical reason from airline ops.

        Returns:
            Human-readable explanation.  Generic fallback on failure.
        """

    @abstractmethod
    async def get_flight_context(
        self,
        flight_number: str,
        date: str,
    ) -> FlightContext:
        """Get contextual intelligence about a flight (weather, NOTAMs).

        Args:
            flight_number: IATA flight number.
            date: Date string (yyyy-MM-dd).

        Returns:
            Structured context.  Empty FlightContext on failure.
        """

    @abstractmethod
    async def describe_option(
        self,
        option_type: str,
        details: dict[str, str],
    ) -> str:
        """Describe a recovery option in passenger-friendly language.

        Args:
            option_type: Type of option (e.g. "rebooking", "hotel").
            details: Key-value pairs describing the option.

        Returns:
            Plain-language description.  Terse fallback on failure.
        """
