# Requires: google-genai
# Install: uv add google-genai
#
# Environment variables:
#   GEMINI_API_KEY — required, Google AI API key
#
# SDK docs: https://ai.google.dev/gemini-api/docs/
# Search grounding: https://ai.google.dev/gemini-api/docs/google-search
# Maps grounding: https://ai.google.dev/gemini-api/docs/maps-grounding

import json
import logging
import os
from dataclasses import dataclass, field

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

# Well-known airport coordinates for Maps grounding context.
# Extend as needed — covers major European hubs relevant to Lufthansa.
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "MUC": (48.3537, 11.7750),
    "FRA": (50.0379, 8.5622),
    "BER": (52.3667, 13.5033),
    "HAM": (53.6304, 9.9882),
    "DUS": (51.2895, 6.7668),
    "VIE": (48.1103, 16.5697),
    "ZRH": (47.4647, 8.5492),
    "CDG": (49.0097, 2.5479),
    "LHR": (51.4700, -0.4543),
    "AMS": (52.3105, 4.7683),
    "FCO": (41.8003, 12.2389),
    "BCN": (41.2974, 2.0833),
    "JFK": (40.6413, -73.7781),
    "ORD": (41.9742, -87.9073),
    "NRT": (35.7720, 140.3929),
}

MODEL = "gemini-2.5-flash"


@dataclass(frozen=True, slots=True)
class TransportOption:
    """A ground transport alternative."""

    mode: str
    provider: str
    route: str
    departure: str
    arrival: str
    duration: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class HotelOption:
    """A nearby hotel option."""

    name: str
    address: str
    distance: str
    price_range: str = ""
    rating: str = ""
    maps_uri: str = ""


@dataclass(frozen=True, slots=True)
class FlightContext:
    """Contextual information about a flight and its route."""

    weather_origin: str = ""
    weather_destination: str = ""
    disruption_info: str = ""
    airport_status: str = ""
    relevant_events: str = ""
    sources: list[str] = field(default_factory=list)


class GeminiGroundingService:
    """Gemini with Google Search + Maps grounding for disruption management."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            msg = "GEMINI_API_KEY is required"
            raise ValueError(msg)
        self._client = genai.Client(api_key=key)

    def _search_config(self, system: str) -> types.GenerateContentConfig:
        """Config with Google Search grounding enabled."""
        return types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

    def _maps_config(
        self,
        system: str,
        lat: float,
        lng: float,
    ) -> types.GenerateContentConfig:
        """Config with Google Maps grounding enabled."""
        return types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(google_maps=types.GoogleMaps())],
            tool_config=types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=types.LatLng(latitude=lat, longitude=lng),
                ),
            ),
        )

    def _coords_for(self, airport_code: str) -> tuple[float, float]:
        """Resolve airport code to lat/lng, falling back to Frankfurt."""
        code = airport_code.upper().strip()
        return AIRPORT_COORDS.get(code, AIRPORT_COORDS["FRA"])

    def _extract_sources(self, response: types.GenerateContentResponse) -> list[str]:
        """Extract grounding source URIs from a response."""
        sources: list[str] = []
        if not response.candidates:
            return sources
        candidate = response.candidates[0]
        metadata = candidate.grounding_metadata
        if metadata and metadata.grounding_chunks:
            for chunk in metadata.grounding_chunks:
                if chunk.web and chunk.web.uri:
                    sources.append(chunk.web.uri)
                elif chunk.maps and chunk.maps.uri:
                    sources.append(chunk.maps.uri)
        return sources

    async def explain_disruption(
        self,
        disruption_type: str,
        flight_number: str,
        origin: str,
        destination: str,
        raw_reason: str,
    ) -> str:
        """Generate a compassionate, plain-language disruption explanation.

        Uses Google Search grounding for real-time context (weather, NOTAMs,
        airport status).

        Args:
            disruption_type: Category — e.g. "cancellation", "delay", "diversion"
            flight_number: IATA flight number, e.g. "LH1234"
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            raw_reason: Technical reason from the airline ops system

        Returns:
            Human-readable explanation suitable for passenger display.
        """
        prompt = (
            f"A passenger's flight {flight_number} from {origin} to {destination} "
            f"has been affected by a {disruption_type}. "
            f"The airline operations system reports: \"{raw_reason}\"\n\n"
            "Search for current real-time information about conditions at both "
            "airports and any relevant weather, NOTAM, or operational issues. "
            "Then write a clear, empathetic explanation for the passenger. "
            "Be factual but compassionate. Keep it under 150 words. "
            "Do NOT use airline jargon. Do NOT speculate beyond what the data shows."
        )
        system = (
            "You are a passenger communication assistant for an airline. "
            "Your tone is calm, empathetic, and informative. "
            "Always ground your explanation in verifiable facts."
        )
        config = self._search_config(system)

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception:
            log.exception("explain_disruption failed for %s", flight_number)
            return (
                f"Your flight {flight_number} from {origin} to {destination} "
                f"has experienced a {disruption_type}. "
                "We are working to provide you with alternatives as quickly as possible."
            )

    async def find_ground_transport(
        self,
        origin_airport: str,
        destination: str,
    ) -> list[TransportOption]:
        """Find ground transport alternatives (train, bus, ride-share).

        Uses Google Maps grounding for routes and travel times.

        Args:
            origin_airport: IATA code of the departure airport
            destination: City name or airport code of final destination

        Returns:
            List of transport options sorted by travel time.
        """
        lat, lng = self._coords_for(origin_airport)
        prompt = (
            f"Find ground transport options from {origin_airport} airport to {destination}. "
            "Include trains, buses, and any other public transit. "
            "For each option provide: mode of transport, provider/operator name, "
            "route description, approximate next departure time, arrival time, "
            "and total duration. "
            "Return ONLY valid JSON — an array of objects with keys: "
            "mode, provider, route, departure, arrival, duration, notes. "
            "No markdown, no explanation, just the JSON array."
        )
        system = (
            "You are a travel logistics assistant. Return only valid JSON arrays. "
            "Be precise about travel times and routes."
        )
        config = self._maps_config(system, lat, lng)

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            return self._parse_transport_options(response.text or "[]")
        except Exception:
            log.exception(
                "find_ground_transport failed for %s -> %s",
                origin_airport,
                destination,
            )
            return []

    async def find_nearby_hotels(
        self,
        airport_code: str,
        max_results: int = 5,
    ) -> list[HotelOption]:
        """Find nearby hotels to an airport.

        Uses Google Maps grounding for hotel search and proximity.

        Args:
            airport_code: IATA airport code
            max_results: Maximum number of results to return

        Returns:
            List of hotel options with name, address, distance.
        """
        lat, lng = self._coords_for(airport_code)
        prompt = (
            f"Find up to {max_results} hotels near {airport_code} airport that "
            "would be suitable for stranded airline passengers. "
            "Prioritize proximity and availability of shuttle service. "
            "For each hotel provide: name, address, approximate distance from "
            "airport, price range, and rating. "
            "Return ONLY valid JSON — an array of objects with keys: "
            "name, address, distance, price_range, rating. "
            "No markdown, no explanation, just the JSON array."
        )
        system = (
            "You are a travel accommodation assistant. Return only valid JSON arrays. "
            "Focus on practical options for stranded travelers."
        )
        config = self._maps_config(system, lat, lng)

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            sources = self._extract_sources(response)
            return self._parse_hotel_options(response.text or "[]", sources)
        except Exception:
            log.exception("find_nearby_hotels failed for %s", airport_code)
            return []

    async def get_flight_context(
        self,
        flight_number: str,
        date: str,
    ) -> FlightContext:
        """Get contextual information about a flight's route.

        Uses Google Search grounding for weather, events, disruptions.

        Args:
            flight_number: IATA flight number, e.g. "LH1234"
            date: Date string, e.g. "2026-02-28"

        Returns:
            Structured context data about the flight.
        """
        prompt = (
            f"Search for current conditions relevant to flight {flight_number} "
            f"on {date}. Find:\n"
            "1. Weather conditions at origin and destination airports\n"
            "2. Any disruptions, delays, or NOTAMs at those airports\n"
            "3. Airport operational status\n"
            "4. Any relevant events (strikes, security incidents, severe weather)\n\n"
            "Return ONLY valid JSON with keys: weather_origin, weather_destination, "
            "disruption_info, airport_status, relevant_events. "
            "Each value should be a concise string. "
            "No markdown, no explanation, just the JSON object."
        )
        system = (
            "You are a flight operations intelligence assistant. "
            "Provide factual, concise information grounded in real-time data."
        )
        config = self._search_config(system)

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            sources = self._extract_sources(response)
            return self._parse_flight_context(response.text or "{}", sources)
        except Exception:
            log.exception("get_flight_context failed for %s", flight_number)
            return FlightContext()

    async def describe_option(
        self,
        option_type: str,
        details: dict[str, str],
    ) -> str:
        """Generate a clear, passenger-friendly description of a rebooking option.

        Args:
            option_type: Type of option — e.g. "rebooking", "ground_transport",
                        "hotel", "refund"
            details: Key-value pairs describing the option

        Returns:
            Passenger-friendly text explaining the option.
        """
        details_text = "\n".join(f"- {k}: {v}" for k, v in details.items())
        prompt = (
            f"Write a clear, friendly description of this {option_type} option "
            f"for an airline passenger:\n{details_text}\n\n"
            "Keep it under 80 words. Be helpful and reassuring. "
            "Include any practical tips (e.g. where to go, what to bring). "
            "Do not use airline jargon."
        )
        system = (
            "You are a passenger communication assistant. "
            "Write clear, warm, helpful descriptions."
        )
        config = types.GenerateContentConfig(system_instruction=system)

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception:
            log.exception("describe_option failed for %s", option_type)
            return f"Option: {option_type}. " + ", ".join(
                f"{k}: {v}" for k, v in details.items()
            )

    # -- Parsing helpers --

    @staticmethod
    def _parse_transport_options(raw: str) -> list[TransportOption]:
        """Parse JSON response into TransportOption list."""
        try:
            # Strip markdown fences if model wraps output
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            items = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            log.warning("Failed to parse transport JSON: %s", raw[:200])
            return []

        results: list[TransportOption] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                TransportOption(
                    mode=str(item.get("mode", "")),
                    provider=str(item.get("provider", "")),
                    route=str(item.get("route", "")),
                    departure=str(item.get("departure", "")),
                    arrival=str(item.get("arrival", "")),
                    duration=str(item.get("duration", "")),
                    notes=str(item.get("notes", "")),
                )
            )
        return results

    @staticmethod
    def _parse_hotel_options(
        raw: str,
        sources: list[str],
    ) -> list[HotelOption]:
        """Parse JSON response into HotelOption list."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            items = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            log.warning("Failed to parse hotel JSON: %s", raw[:200])
            return []

        results: list[HotelOption] = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            maps_uri = sources[i] if i < len(sources) else ""
            results.append(
                HotelOption(
                    name=str(item.get("name", "")),
                    address=str(item.get("address", "")),
                    distance=str(item.get("distance", "")),
                    price_range=str(item.get("price_range", "")),
                    rating=str(item.get("rating", "")),
                    maps_uri=maps_uri,
                )
            )
        return results

    @staticmethod
    def _parse_flight_context(
        raw: str,
        sources: list[str],
    ) -> FlightContext:
        """Parse JSON response into FlightContext."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            log.warning("Failed to parse flight context JSON: %s", raw[:200])
            return FlightContext()

        if not isinstance(data, dict):
            return FlightContext()

        return FlightContext(
            weather_origin=str(data.get("weather_origin", "")),
            weather_destination=str(data.get("weather_destination", "")),
            disruption_info=str(data.get("disruption_info", "")),
            airport_status=str(data.get("airport_status", "")),
            relevant_events=str(data.get("relevant_events", "")),
            sources=sources,
        )
