"""Static data adapter — fallback for offline operation.

Extracts all static lookup tables from option_generator.py and implements
both GroundingPort and FlightDataPort using only hardcoded data.
No API calls, no external dependencies, all deterministic.
"""

from __future__ import annotations

from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.services.gemini import FlightContext, HotelOption, TransportOption

# ---------------------------------------------------------------------------
# Rebook templates: destination -> [(flight, origin, dest, dep_h, dep_m)]
# ---------------------------------------------------------------------------
_REBOOK_TEMPLATES: dict[str, list[tuple[str, str, str, int, int]]] = {
    "FRA": [
        ("LH98", "MUC", "FRA", 6, 30),
        ("LH100", "MUC", "FRA", 8, 0),
        ("LH102", "MUC", "FRA", 10, 15),
        ("LH104", "MUC", "FRA", 14, 45),
    ],
    "CDG": [
        ("LH1836", "MUC", "CDG", 7, 15),
        ("LH1838", "MUC", "CDG", 11, 30),
        ("LH1840", "MUC", "CDG", 16, 0),
    ],
    "FCO": [("LH2032", "MUC", "FCO", 7, 45), ("LH2034", "MUC", "FCO", 13, 20)],
    "BCN": [("LH1858", "MUC", "BCN", 8, 0), ("LH1860", "MUC", "BCN", 15, 10)],
    "ZRH": [
        ("LH1612", "MUC", "ZRH", 6, 45),
        ("LH1614", "MUC", "ZRH", 12, 0),
        ("LH1616", "MUC", "ZRH", 17, 30),
    ],
    "LHR": [("LH2472", "MUC", "LHR", 7, 0), ("LH2474", "MUC", "LHR", 14, 0)],
    "AMS": [("LH2308", "MUC", "AMS", 6, 50), ("LH2310", "MUC", "AMS", 13, 45)],
    "VIE": [("LH1676", "MUC", "VIE", 7, 30), ("OS112", "MUC", "VIE", 10, 0)],
}

# Star Alliance partners for rebooking scope expansion
_STAR_ALLIANCE_FLIGHTS: dict[str, list[tuple[str, str, str, int, int]]] = {
    "FRA": [("LX1071", "MUC", "FRA", 9, 0), ("OS123", "MUC", "FRA", 11, 0)],
    "CDG": [("SN2594", "MUC", "CDG", 9, 45)],
    "LHR": [("LX317", "MUC", "LHR", 10, 30)],
    "AMS": [("LX1081", "MUC", "AMS", 8, 30)],
}

# Non-Star Alliance options (for HON Circle "any airline" scope)
_ANY_AIRLINE_FLIGHTS: dict[str, list[tuple[str, str, str, int, int]]] = {
    "FRA": [("EW9040", "MUC", "FRA", 7, 30)],
    "CDG": [("AF1523", "MUC", "CDG", 8, 45)],
    "LHR": [("BA957", "MUC", "LHR", 9, 15)],
    "BCN": [("VY1817", "MUC", "BCN", 10, 0)],
}

# ---------------------------------------------------------------------------
# Fallback hotel data by star rating
# (name, address, lat, lng, stars, price_eur, rating_str)
# ---------------------------------------------------------------------------
_HOTELS_BY_TIER: dict[int, list[tuple[str, str, float, float, int, int, str]]] = {
    5: [
        ("Hilton Munich Airport", "Terminalstr. Mitte 20, 85356 Freising",
         48.3533, 11.7867, 5, 200, "4.5"),
        ("Kempinski Hotel Airport Muenchen", "Muenchner Str. 2, 85354 Freising",
         48.3601, 11.7811, 5, 220, "4.6"),
    ],
    4: [
        ("NH Munich Airport", "Lohstr. 21, 85445 Oberding",
         48.3325, 11.8203, 4, 140, "4.2"),
        ("Novotel Muenchen Airport", "Nordallee 29, 85356 Freising",
         48.3561, 11.7833, 4, 130, "4.1"),
    ],
    3: [
        ("Ibis Muenchen Airport Sued", "Ismaninger Str. 7, 85675 Eitting",
         48.3419, 11.8956, 3, 85, "3.8"),
        ("Holiday Inn Express Munich Airport", "Freisinger Str. 94, 85716 Unterschleissheim",
         48.2833, 11.5667, 3, 79, "3.7"),
    ],
}

# ---------------------------------------------------------------------------
# Ground transport routes: dest -> [(route, provider, hours, mode)]
# ---------------------------------------------------------------------------
_GROUND_ROUTES: dict[str, list[tuple[str, str, int, str]]] = {
    "FRA": [
        ("ICE Munich Hbf - Frankfurt Hbf", "Deutsche Bahn", 3, "train"),
        ("FlixBus Munich ZOB - Frankfurt Hbf", "FlixBus", 5, "bus"),
    ],
    "ZRH": [
        ("EC Munich Hbf - Zurich HB", "Deutsche Bahn / SBB", 4, "train"),
    ],
    "CDG": [
        ("ICE Munich Hbf - Paris Est", "Deutsche Bahn / SNCF", 6, "train"),
    ],
    "VIE": [
        ("RJX Munich Hbf - Wien Hbf", "OeBB", 4, "train"),
    ],
    "AMS": [
        ("ICE Munich Hbf - Amsterdam Centraal", "Deutsche Bahn / NS", 7, "train"),
    ],
}

# ---------------------------------------------------------------------------
# Alt-airport routing templates
# ---------------------------------------------------------------------------
_ALT_AIRPORT_ROUTES: dict[str, list[dict[str, str | int]]] = {
    "FRA": [
        {"via": "NUE", "flight": "LH190", "transfer": "train", "total_hours": 4},
        {"via": "STR", "flight": "LH1192", "transfer": "train", "total_hours": 5},
    ],
    "CDG": [
        {"via": "ZRH", "flight": "LX638", "transfer": "train", "total_hours": 6},
    ],
    "LHR": [
        {"via": "FRA", "flight": "LH920", "transfer": "bus", "total_hours": 5},
    ],
}

# HON Circle gets more creative routing options
_ALT_AIRPORT_ROUTES_HON: dict[str, list[dict[str, str | int]]] = {
    "FRA": [
        {"via": "DUS", "flight": "EW9520", "transfer": "taxi", "total_hours": 3},
    ],
    "CDG": [
        {"via": "BRU", "flight": "SN2592", "transfer": "taxi", "total_hours": 4},
    ],
    "LHR": [
        {"via": "AMS", "flight": "KL1024", "transfer": "taxi", "total_hours": 4},
    ],
}

# ---------------------------------------------------------------------------
# LH Lounge data by airport -> access tier
# ---------------------------------------------------------------------------
_LOUNGES: dict[str, dict[str, list[dict]]] = {
    "MUC": {
        "first_class": [{
            "name": "Lufthansa First Class Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["A-la-carte dining", "Premium bar", "Sleeping rooms",
                          "Shower suites", "Personal assistant", "Limousine service"],
            "opening_hours": "05:30-23:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }],
        "senator": [{
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["Hot & cold buffet", "Premium drinks", "Showers",
                          "Workstations", "Quiet zone", "Priority boarding"],
            "opening_hours": "05:30-23:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 2",
            "location": "Gate area G, Level 2",
            "amenities": ["Hot & cold buffet", "Bar", "Showers", "Workstations"],
            "opening_hours": "05:30-22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }],
        "business": [{
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations", "Wi-Fi"],
            "opening_hours": "05:30-23:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 2",
            "location": "Gate area G, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations"],
            "opening_hours": "05:30-22:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }],
    },
    "FRA": {
        "first_class": [{
            "name": "Lufthansa First Class Terminal",
            "terminal": "Dedicated building near Terminal 1",
            "location": "Separate entrance, limousine to aircraft",
            "amenities": ["Fine dining", "Cigar lounge", "Bath & shower suites",
                          "Sleeping rooms", "Personal assistant", "Porsche transfer to gate"],
            "opening_hours": "06:00-22:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }, {
            "name": "Lufthansa First Class Lounge",
            "terminal": "Terminal 1, Pier A",
            "location": "Near gate A26",
            "amenities": ["A-la-carte dining", "Premium bar", "Shower suites",
                          "Sleeping chairs", "Personal assistant"],
            "opening_hours": "06:00-22:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }],
        "senator": [{
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 1, Pier A/Z",
            "location": "Gate area A",
            "amenities": ["Hot & cold buffet", "Premium drinks", "Showers",
                          "Workstations", "Quiet zone"],
            "opening_hours": "06:00-22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 1, Pier B",
            "location": "Gate area B, Level 2",
            "amenities": ["Buffet", "Bar", "Showers", "Workstations"],
            "opening_hours": "06:00-22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }],
        "business": [{
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 1, Pier A",
            "location": "Gate area A, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations", "Wi-Fi"],
            "opening_hours": "06:00-22:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 1, Pier B",
            "location": "Gate area B",
            "amenities": ["Buffet", "Drinks", "Workstations"],
            "opening_hours": "06:00-22:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }],
    },
    "NUE": {
        "business": [{
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 1",
            "location": "Gate area, Level 1",
            "amenities": ["Snacks", "Drinks", "Wi-Fi", "Workstations"],
            "opening_hours": "06:00-20:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }],
    },
}

# Lounge access tier -> LH API tier_code mapping
_TIER_CODE_MAP: dict[str, str] = {
    "first_class": "HON",
    "senator": "SEN",
    "business": "FTL",
}

# Meal voucher accepted locations by airport
_MEAL_VOUCHER_RESTAURANTS: dict[str, list[str]] = {
    "MUC": ["Airbraeu", "Burger King T2", "Cafe Mueller", "Vinzenzmurr",
            "L'Osteria", "Paulaner", "Starbucks T2"],
    "FRA": ["Goethe Bar", "7Bar", "McDonald's T1", "Rewe To Go",
            "Cafe Extrablatt", "Asia Gourmet", "Starbucks T1"],
    "NUE": ["Airport Bistro", "Lebkuchen Schmidt", "Starbucks"],
}

# ---------------------------------------------------------------------------
# Disruption explanation templates
# ---------------------------------------------------------------------------
_EXPLANATION_TEMPLATES: dict[str, str] = {
    "cancellation": (
        "Your flight {flight} from {origin} to {destination} has been cancelled. "
        "Reason: {reason}. We sincerely apologize for the inconvenience and are "
        "working to get you to your destination as quickly as possible."
    ),
    "delay": (
        "Your flight {flight} from {origin} to {destination} is experiencing a delay. "
        "Reason: {reason}. We apologize for the inconvenience and will keep you updated."
    ),
    "diversion": (
        "Your flight {flight} from {origin} to {destination} has been diverted. "
        "Reason: {reason}. We are arranging alternative transport to your destination."
    ),
    "gate_change": (
        "Your flight {flight} from {origin} to {destination} has a gate change. "
        "Reason: {reason}. Please proceed to the new gate."
    ),
}


class StaticDataAdapter(FlightDataPort, GroundingPort):
    """Fallback adapter with hardcoded static data for offline operation.

    Implements both FlightDataPort and GroundingPort using only in-memory
    static dictionaries.  No API calls, no I/O, fully deterministic.
    """

    # ------------------------------------------------------------------
    # GroundingPort
    # ------------------------------------------------------------------

    async def find_nearby_hotels(
        self,
        airport_code: str,
        max_results: int = 5,
    ) -> list[HotelOption]:
        results: list[HotelOption] = []
        for _stars, hotels in sorted(_HOTELS_BY_TIER.items(), reverse=True):
            for name, address, _lat, _lng, _s, _price, rating in hotels:
                results.append(HotelOption(
                    name=name,
                    address=address,
                    distance="near airport",
                    price_range=f"{_price} EUR",
                    rating=rating,
                    maps_uri="",
                ))
                if len(results) >= max_results:
                    return results
        return results

    async def find_ground_transport(
        self,
        origin_airport: str,
        destination: str,
    ) -> list[TransportOption]:
        dest = destination.upper().strip()
        routes = _GROUND_ROUTES.get(dest, [])
        results: list[TransportOption] = []
        for route_desc, provider, hours, mode in routes:
            results.append(TransportOption(
                mode=mode,
                provider=provider,
                route=route_desc,
                departure="",
                arrival="",
                duration=f"{hours}h",
            ))
        return results

    async def explain_disruption(
        self,
        disruption_type: str,
        flight_number: str,
        origin: str,
        destination: str,
        raw_reason: str,
    ) -> str:
        template = _EXPLANATION_TEMPLATES.get(
            disruption_type.lower(),
            (
                "Your flight {flight} from {origin} to {destination} has been "
                "disrupted. Reason: {reason}. We apologize for the inconvenience."
            ),
        )
        return template.format(
            flight=flight_number,
            origin=origin,
            destination=destination,
            reason=raw_reason,
        )

    async def get_flight_context(
        self,
        flight_number: str,
        date: str,
    ) -> FlightContext:
        return FlightContext()

    async def describe_option(
        self,
        option_type: str,
        details: dict[str, str],
    ) -> str:
        return ""

    # ------------------------------------------------------------------
    # FlightDataPort
    # ------------------------------------------------------------------

    async def get_schedules(
        self,
        origin: str,
        destination: str,
        date: str,
        *,
        direct_flights: bool = False,
    ) -> dict:
        dest = destination.upper().strip()
        orig = origin.upper().strip()

        templates = _REBOOK_TEMPLATES.get(dest, [])
        # Filter to matching origin
        templates = [t for t in templates if t[1] == orig]

        if not templates:
            return {}

        schedules = []
        for flight, dep_airport, arr_airport, dep_h, dep_m in templates:
            schedules.append({
                "Flight": {
                    "MarketingCarrier": {
                        "AirlineID": flight[:2],
                        "FlightNumber": flight[2:],
                    },
                    "Departure": {
                        "AirportCode": dep_airport,
                        "ScheduledTimeLocal": {
                            "DateTime": f"{date}T{dep_h:02d}:{dep_m:02d}",
                        },
                    },
                    "Arrival": {
                        "AirportCode": arr_airport,
                    },
                },
            })

        return {"ScheduleResource": {"Schedule": schedules}}

    async def get_lounges(
        self,
        airport_code: str,
        *,
        tier_code: str | None = None,
        cabin_class: str | None = None,
    ) -> dict:
        airport_lounges = _LOUNGES.get(airport_code.upper(), {})
        if not airport_lounges:
            return {}

        # Map tier_code back to access tier name
        tier_to_access = {v: k for k, v in _TIER_CODE_MAP.items()}
        access_tier = tier_to_access.get(tier_code, "") if tier_code else ""

        matched: list[dict] = []
        if access_tier and access_tier in airport_lounges:
            matched = airport_lounges[access_tier]
        else:
            # Return all lounges for the airport
            for tier_list in airport_lounges.values():
                matched.extend(tier_list)

        if not matched:
            return {}

        lounges_out = []
        for lounge in matched:
            lounges_out.append({
                "Names": {"Name": [{"$": lounge["name"], "@LanguageCode": "en"}]},
                "Locations": {"Location": [{"$": lounge["location"], "@LanguageCode": "en"}]},
                "OpeningHours": {"OpeningHour": [{"$": lounge["opening_hours"], "@LanguageCode": "en"}]},
                "Features": {
                    "ShowerFacilities": str(lounge.get("shower_available", False)).lower(),
                    "RelaxingRooms": str(lounge.get("sleeping_rooms", False)).lower(),
                },
            })

        return {"LoungeResource": {"Lounges": {"Lounge": lounges_out}}}

    async def get_flight_status(
        self,
        flight_number: str,
        date: str,
    ) -> dict:
        return {}

    async def get_seat_map(
        self,
        flight_number: str,
        origin: str,
        destination: str,
        date: str,
        cabin_class: str,
    ) -> dict:
        return {}

    async def get_nearest_airports(self, latitude: float, longitude: float) -> dict:
        return {}

    async def get_airport_info(self, airport_code: str) -> dict:
        return {}


# ---------------------------------------------------------------------------
# Public helpers for option_generator access to raw static data
# ---------------------------------------------------------------------------

def get_rebook_templates() -> dict[str, list[tuple[str, str, str, int, int]]]:
    return _REBOOK_TEMPLATES


def get_star_alliance_flights() -> dict[str, list[tuple[str, str, str, int, int]]]:
    return _STAR_ALLIANCE_FLIGHTS


def get_any_airline_flights() -> dict[str, list[tuple[str, str, str, int, int]]]:
    return _ANY_AIRLINE_FLIGHTS


def get_hotels_by_tier() -> dict[int, list[tuple[str, str, float, float, int, int, str]]]:
    return _HOTELS_BY_TIER


def get_ground_routes() -> dict[str, list[tuple[str, str, int, str]]]:
    return _GROUND_ROUTES


def get_alt_airport_routes() -> dict[str, list[dict[str, str | int]]]:
    return _ALT_AIRPORT_ROUTES


def get_alt_airport_routes_hon() -> dict[str, list[dict[str, str | int]]]:
    return _ALT_AIRPORT_ROUTES_HON


def get_lounges() -> dict[str, dict[str, list[dict]]]:
    return _LOUNGES


def get_tier_code_map() -> dict[str, str]:
    return _TIER_CODE_MAP


def get_meal_voucher_restaurants() -> dict[str, list[str]]:
    return _MEAL_VOUCHER_RESTAURANTS
