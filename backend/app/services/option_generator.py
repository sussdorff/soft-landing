"""Option Generator — creates rebooking/hotel/ground/alt options for passengers.

Integrates Gemini Grounding (Google Maps) for real hotel/transport data,
with deterministic fallbacks when the API is unavailable.  Options are
differentiated by passenger loyalty tier and booking class.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import OptionRow
from app.models import (
    BookingClass,
    DisruptionType,
    LoyaltyTier,
)
from app.store import compute_service_level

from sqlalchemy import select as sa_select

if TYPE_CHECKING:
    from app.models import ServiceLevel
    from app.services.gemini import GeminiGroundingService, HotelOption
    from app.services.lufthansa import LufthansaClient

log = logging.getLogger(__name__)

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

# ---------------------------------------------------------------------------
# LH Lounge data by airport → access tier
# ---------------------------------------------------------------------------
_LOUNGES: dict[str, dict[str, list[dict]]] = {
    "MUC": {
        "first_class": [{
            "name": "Lufthansa First Class Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["A-la-carte dining", "Premium bar", "Sleeping rooms",
                          "Shower suites", "Personal assistant", "Limousine service"],
            "opening_hours": "05:30–23:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }],
        "senator": [{
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["Hot & cold buffet", "Premium drinks", "Showers",
                          "Workstations", "Quiet zone", "Priority boarding"],
            "opening_hours": "05:30–23:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 2",
            "location": "Gate area G, Level 2",
            "amenities": ["Hot & cold buffet", "Bar", "Showers", "Workstations"],
            "opening_hours": "05:30–22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }],
        "business": [{
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 2, Satellite",
            "location": "Gate area H, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations", "Wi-Fi"],
            "opening_hours": "05:30–23:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 2",
            "location": "Gate area G, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations"],
            "opening_hours": "05:30–22:00",
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
            "opening_hours": "06:00–22:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }, {
            "name": "Lufthansa First Class Lounge",
            "terminal": "Terminal 1, Pier A",
            "location": "Near gate A26",
            "amenities": ["A-la-carte dining", "Premium bar", "Shower suites",
                          "Sleeping chairs", "Personal assistant"],
            "opening_hours": "06:00–22:00",
            "shower_available": True,
            "sleeping_rooms": True,
        }],
        "senator": [{
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 1, Pier A/Z",
            "location": "Gate area A",
            "amenities": ["Hot & cold buffet", "Premium drinks", "Showers",
                          "Workstations", "Quiet zone"],
            "opening_hours": "06:00–22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Senator Lounge",
            "terminal": "Terminal 1, Pier B",
            "location": "Gate area B, Level 2",
            "amenities": ["Buffet", "Bar", "Showers", "Workstations"],
            "opening_hours": "06:00–22:00",
            "shower_available": True,
            "sleeping_rooms": False,
        }],
        "business": [{
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 1, Pier A",
            "location": "Gate area A, Level 2",
            "amenities": ["Buffet", "Drinks", "Workstations", "Wi-Fi"],
            "opening_hours": "06:00–22:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }, {
            "name": "Lufthansa Business Lounge",
            "terminal": "Terminal 1, Pier B",
            "location": "Gate area B",
            "amenities": ["Buffet", "Drinks", "Workstations"],
            "opening_hours": "06:00–22:00",
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
            "opening_hours": "06:00–20:00",
            "shower_available": False,
            "sleeping_rooms": False,
        }],
    },
}

# Lounge access tier → LH API tier_code mapping
_TIER_CODE_MAP: dict[str, str] = {
    "first_class": "HON",
    "senator": "SEN",
    "business": "FTL",
}

# Meal voucher accepted locations by airport
_MEAL_VOUCHER_RESTAURANTS: dict[str, list[str]] = {
    "MUC": ["Airbräu", "Burger King T2", "Café Müller", "Vinzenzmurr",
            "L'Osteria", "Paulaner", "Starbucks T2"],
    "FRA": ["Goethe Bar", "7Bar", "McDonald's T1", "Rewe To Go",
            "Café Extrablatt", "Asia Gourmet", "Starbucks T1"],
    "NUE": ["Airport Bistro", "Lebkuchen Schmidt", "Starbucks"],
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


class OptionGenerator:
    """Generates travel options for disrupted passengers.

    When a ``GeminiGroundingService`` is provided, hotel and transport
    lookups use live Google Maps data.  Otherwise deterministic fallback
    data is used so the system works without an API key.
    """

    def __init__(
        self,
        gemini: GeminiGroundingService | None = None,
        lh_client: LufthansaClient | None = None,
    ) -> None:
        self.gemini = gemini
        self.lh_client = lh_client

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate_options(
        self,
        session: AsyncSession,
        disruption_id: str,
        passenger_id: str,
        disruption_type: DisruptionType,
        destination: str,
        base_time: datetime,
        loyalty_tier: LoyaltyTier = LoyaltyTier.NONE,
        booking_class: BookingClass = BookingClass.Y,
    ) -> list[str]:
        """Generate and persist option rows for a disrupted passenger.

        Returns a list of the created option IDs.
        """
        if disruption_type == DisruptionType.GATE_CHANGE:
            return []  # Gate changes don't need rebooking options

        svc = compute_service_level(loyalty_tier, booking_class)
        option_ids: list[str] = []

        # 1. Rebook (may call LH Schedules API)
        opt_id = await self._add_rebook_option(
            session, passenger_id, destination, base_time, svc, loyalty_tier,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 2. Hotel (may call Gemini)
        opt_id = await self._add_hotel_option(
            session, passenger_id, destination, base_time, svc,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 3. Ground transport (may call Gemini)
        opt_id = await self._add_ground_option(
            session, passenger_id, destination, base_time, svc, loyalty_tier,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 4. Alt-airport (cancellations / diversions only)
        if disruption_type in (DisruptionType.CANCELLATION, DisruptionType.DIVERSION):
            opt_id = self._add_alt_airport_option(
                session, passenger_id, destination, base_time, loyalty_tier,
            )
            if opt_id:
                option_ids.append(opt_id)

        # 5. Lounge access (if eligible, may call LH Lounge API)
        opt_id = await self._add_lounge_option(
            session, passenger_id, base_time, svc, "MUC",
        )
        if opt_id:
            option_ids.append(opt_id)

        # 6. Meal voucher (if no lounge access)
        opt_id = self._add_voucher_option(
            session, passenger_id, base_time, svc, "MUC",
        )
        if opt_id:
            option_ids.append(opt_id)

        # 7. Enrich descriptions with Gemini (nice-to-have, never blocks)
        if self.gemini is not None:
            await self._enrich_descriptions(session, passenger_id)

        return option_ids

    # ------------------------------------------------------------------
    # Gemini description enrichment
    # ------------------------------------------------------------------

    async def _enrich_descriptions(
        self,
        session: AsyncSession,
        passenger_id: str,
    ) -> None:
        """Use Gemini to generate richer, passenger-friendly descriptions.

        This is a best-effort enrichment — failures are logged but never
        propagated.  The original descriptions remain if Gemini fails.
        """
        try:
            stmt = sa_select(OptionRow).where(OptionRow.passenger_id == passenger_id)
            rows = (await session.execute(stmt)).scalars().all()
            for row in rows:
                try:
                    details = row.details_json if isinstance(row.details_json, dict) else {}
                    # Convert all values to strings for the Gemini prompt
                    details_str = {k: str(v) for k, v in details.items()}
                    enriched = await self.gemini.describe_option(row.type, details_str)
                    if enriched:
                        row.description = enriched
                except Exception:
                    log.exception("Gemini describe_option failed for %s", row.id)
        except Exception:
            log.exception("_enrich_descriptions failed for passenger %s", passenger_id)

    # ------------------------------------------------------------------
    # Rebook
    # ------------------------------------------------------------------

    async def _add_rebook_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        next_day = base_time + timedelta(days=1)
        dest = destination.upper().strip()
        next_day_str = next_day.strftime("%Y-%m-%d")

        # Try LH Schedules API for real flight data
        lh_candidates = await self._fetch_lh_schedules(dest, next_day_str)

        # Build candidate flights based on rebooking scope
        candidates: list[tuple[str, str, str, int, int]] = []

        if lh_candidates:
            candidates.extend(lh_candidates)
        else:
            candidates.extend(_REBOOK_TEMPLATES.get(dest, []))

        if svc.rebooking_scope in ("star_alliance", "any_airline"):
            candidates.extend(_STAR_ALLIANCE_FLIGHTS.get(dest, []))

        if svc.rebooking_scope == "any_airline":
            candidates.extend(_ANY_AIRLINE_FLIGHTS.get(dest, []))

        # Pick the earliest available flight
        if candidates:
            candidates.sort(key=lambda t: (t[3], t[4]))
            tpl = candidates[0]
            dep = next_day.replace(
                hour=tpl[3], minute=tpl[4], second=0, microsecond=0,
            )
            arr = dep + timedelta(hours=1, minutes=30)

            # Build description with rebooking scope info
            scope_note = self._rebooking_scope_note(svc, loyalty_tier)
            upgrade_note = ""
            if svc.upgrade_eligible:
                upgrade_note = " Upgrade to higher cabin possible if available."

            opt_id = f"opt-{passenger_id}-rebook"
            session.add(OptionRow(
                id=opt_id,
                passenger_id=passenger_id,
                type="rebook",
                summary=f"Rebook {tpl[0]} tomorrow {tpl[3]:02d}:{tpl[4]:02d}",
                description=(
                    f"Next available flight {tpl[0]} {tpl[1]}-{tpl[2]} tomorrow. "
                    f"{scope_note}{upgrade_note}"
                ).strip(),
                details_json={
                    "flight_number": tpl[0],
                    "origin": tpl[1],
                    "destination": tpl[2],
                    "departure": dep.isoformat(),
                    "seat_available": True,
                    "source": "lufthansa_api" if lh_candidates else "static",
                },
                available=True,
                estimated_arrival=arr,
            ))
            return opt_id

        # Generic rebook for unknown destinations
        dep = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
        arr = dep + timedelta(hours=2)
        scope_note = self._rebooking_scope_note(svc, loyalty_tier)
        opt_id = f"opt-{passenger_id}-rebook"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="rebook",
            summary=f"Next available flight to {destination}",
            description=(
                f"Rebooked on next available flight to {destination} tomorrow. "
                f"{scope_note}"
            ).strip(),
            details_json={
                "flight_number": "LHXXXX",
                "origin": "MUC",
                "destination": destination,
                "departure": dep.isoformat(),
                "seat_available": True,
                "source": "static",
            },
            available=True,
            estimated_arrival=arr,
        ))
        return opt_id

    async def _fetch_lh_schedules(
        self,
        destination: str,
        date_str: str,
        origin: str = "MUC",
    ) -> list[tuple[str, str, str, int, int]]:
        """Fetch real schedules from LH API, returning candidates in template format.

        Returns an empty list if the client is unavailable or the API call fails.
        """
        if self.lh_client is None:
            return []

        try:
            data = await self.lh_client.get_schedules(origin, destination, date_str)
        except Exception:
            log.exception("LH Schedules API failed for %s->%s on %s", origin, destination, date_str)
            return []

        candidates: list[tuple[str, str, str, int, int]] = []
        try:
            schedules = data.get("ScheduleResource", {}).get("Schedule", [])
            if isinstance(schedules, dict):
                schedules = [schedules]  # Single result comes as dict
            for sched in schedules:
                flight = sched.get("Flight", {})
                mc = flight.get("MarketingCarrier", {})
                airline_id = mc.get("AirlineID", "")
                flight_num = mc.get("FlightNumber", "")
                flight_code = f"{airline_id}{flight_num}"

                dep_info = flight.get("Departure", {})
                dep_airport = dep_info.get("AirportCode", origin)
                dep_dt_str = dep_info.get("ScheduledTimeLocal", {}).get("DateTime", "")

                arr_info = flight.get("Arrival", {})
                arr_airport = arr_info.get("AirportCode", destination)

                if dep_dt_str and "T" in dep_dt_str:
                    time_part = dep_dt_str.split("T")[1]
                    parts = time_part.split(":")
                    dep_hour = int(parts[0])
                    dep_minute = int(parts[1])
                    candidates.append((flight_code, dep_airport, arr_airport, dep_hour, dep_minute))
        except Exception:
            log.exception("Failed to parse LH Schedules response for %s->%s", origin, destination)
            return []

        if candidates:
            log.info("LH API returned %d schedules for %s->%s on %s", len(candidates), origin, destination, date_str)

        return candidates

    @staticmethod
    def _rebooking_scope_note(svc: ServiceLevel, loyalty_tier: LoyaltyTier) -> str:
        if svc.rebooking_scope == "any_airline":
            return "Rebooking on any airline. Including non-Star Alliance options."
        if svc.rebooking_scope == "star_alliance":
            return "Rebooking across Star Alliance network."
        # lh_group
        if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER:
            return "Rebooking within Lufthansa Group (LH, OS, LX, SN)."
        return "Rebooking within Lufthansa Group."

    # ------------------------------------------------------------------
    # Hotel
    # ------------------------------------------------------------------

    async def _add_hotel_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
    ) -> str | None:
        next_day = base_time + timedelta(days=1)
        next_flight_dep = next_day.replace(hour=7, minute=0, second=0, microsecond=0)

        # Try Gemini for live hotel data
        hotel_data = await self._fetch_gemini_hotel(svc)

        if hotel_data:
            name, address, lat, lng, stars, price, rating, maps_uri = hotel_data
        else:
            # Deterministic fallback
            name, address, lat, lng, stars, price, rating = self._pick_fallback_hotel(svc)
            maps_uri = ""

        star_label = f"{stars}-star" if stars else ""
        budget_note = f" (up to {svc.hotel_budget_eur} EUR/night)" if svc.hotel_budget_eur else ""
        suite_note = ""
        if svc.hotel_stars >= 5:
            suite_note = " Executive Suite or Club Room included."

        opt_id = f"opt-{passenger_id}-hotel"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="hotel",
            summary=f"Overnight at {name}",
            description=(
                f"Complimentary {star_label} stay at {name} with breakfast."
                f"{budget_note}{' ' + suite_note if suite_note else ''}"
            ).strip(),
            details_json={
                "hotel_name": name,
                "address": address,
                "location": {"lat": lat, "lng": lng},
                "next_flight_number": "LHXXXX",
                "next_flight_departure": next_flight_dep.isoformat(),
                "stars": stars,
                "price_per_night": price,
                "maps_uri": maps_uri,
                "rating": rating,
            },
            available=True,
            estimated_arrival=next_day.replace(
                hour=10, minute=0, second=0, microsecond=0,
            ),
        ))
        return opt_id

    async def _fetch_gemini_hotel(
        self,
        svc: ServiceLevel,
    ) -> tuple[str, str, float, float, int, int, str, str] | None:
        """Try to get a suitable hotel from Gemini Maps grounding.

        Returns ``(name, address, lat, lng, stars, price, rating, maps_uri)``
        or ``None`` on failure / when Gemini is unavailable.
        """
        if self.gemini is None:
            return None

        try:
            hotels: list[HotelOption] = await self.gemini.find_nearby_hotels("MUC")
        except Exception:
            log.exception("Gemini hotel lookup failed")
            return None

        if not hotels:
            return None

        # Filter and rank hotels by service level
        best = self._rank_gemini_hotels(hotels, svc)
        if best is None:
            return None

        # Parse price from price_range (e.g. "120-180 EUR") — take midpoint
        price = self._parse_price(best.price_range, svc.hotel_budget_eur)
        rating_str = best.rating or ""
        maps_uri = best.maps_uri or ""

        # We don't get lat/lng from the Gemini result directly, default to airport
        return (best.name, best.address, 48.354, 11.775, svc.hotel_stars, price, rating_str, maps_uri)

    @staticmethod
    def _rank_gemini_hotels(
        hotels: list[HotelOption],
        svc: ServiceLevel,
    ) -> HotelOption | None:
        """Pick the best hotel from Gemini results given the service level."""
        if not hotels:
            return None

        # Sort by rating descending — higher-tier passengers get better hotels
        def _sort_key(h: HotelOption) -> float:
            try:
                return -float(h.rating)
            except (ValueError, TypeError):
                return 0.0

        ranked = sorted(hotels, key=_sort_key)

        # For high-tier (5-star budget), prefer top-rated; for low-tier, prefer cheapest
        if svc.hotel_stars >= 5:
            return ranked[0]
        if svc.hotel_stars >= 4:
            return ranked[min(1, len(ranked) - 1)]
        return ranked[-1]  # Cheapest / lowest-rated for budget tier

    @staticmethod
    def _parse_price(price_range: str, fallback: int) -> int:
        """Extract a numeric price from a string like '120-180 EUR'."""
        if not price_range:
            return fallback
        import re
        numbers = re.findall(r"\d+", price_range)
        if len(numbers) >= 2:
            return (int(numbers[0]) + int(numbers[1])) // 2
        if numbers:
            return int(numbers[0])
        return fallback

    @staticmethod
    def _pick_fallback_hotel(
        svc: ServiceLevel,
    ) -> tuple[str, str, float, float, int, int, str]:
        """Select a deterministic fallback hotel based on service level.

        Returns ``(name, address, lat, lng, stars, price, rating)``.
        """
        target_stars = svc.hotel_stars

        # Walk down from target stars to find available hotels
        for stars in (target_stars, target_stars - 1, target_stars + 1, 3):
            hotels = _HOTELS_BY_TIER.get(stars)
            if hotels:
                h = hotels[0]
                # Cap price at the service-level budget
                price = min(h[5], svc.hotel_budget_eur)
                return (h[0], h[1], h[2], h[3], h[4], price, h[6])

        # Absolute fallback
        return ("Airport Hotel", "Airport Terminal Area", 48.354, 11.775, 3, 80, "3.5")

    # ------------------------------------------------------------------
    # Ground transport
    # ------------------------------------------------------------------

    async def _add_ground_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        dest = destination.upper().strip()

        # HON / Senator: offer taxi/limousine regardless of destination
        if svc.transport_mode in ("limousine", "taxi"):
            return self._add_premium_ground(
                session, passenger_id, dest, base_time, svc, loyalty_tier,
            )

        # Standard passengers: try Gemini for live transport data
        if self.gemini is not None:
            try:
                from app.services.gemini import TransportOption as GeminiTransport  # noqa: F811

                options: list[GeminiTransport] = await self.gemini.find_ground_transport(
                    "MUC", dest,
                )
                if options:
                    best = options[0]
                    ground_dep = base_time + timedelta(hours=2)
                    # Parse duration string for arrival estimate (e.g. "3h", "3 hours")
                    dur_hours = self._parse_duration_hours(best.duration)
                    ground_arr = ground_dep + timedelta(hours=dur_hours)

                    opt_id = f"opt-{passenger_id}-ground"
                    session.add(OptionRow(
                        id=opt_id,
                        passenger_id=passenger_id,
                        type="ground",
                        summary=best.route[:60] if best.route else f"{best.mode} to {dest}",
                        description=(
                            f"{best.route}. Provider: {best.provider}. "
                            f"Duration: {best.duration}."
                        ),
                        details_json={
                            "mode": best.mode,
                            "route": best.route,
                            "departure": ground_dep.isoformat(),
                            "arrival": ground_arr.isoformat(),
                            "provider": best.provider,
                        },
                        available=True,
                        estimated_arrival=ground_arr,
                    ))
                    return opt_id
            except Exception:
                log.exception("Gemini find_ground_transport failed, using fallback")

        # Fallback: static train/bus routes
        routes = _GROUND_ROUTES.get(dest)
        if not routes:
            return None

        route_desc, provider, hours, mode = routes[0]
        ground_dep = base_time + timedelta(hours=2)
        ground_arr = ground_dep + timedelta(hours=hours)

        opt_id = f"opt-{passenger_id}-ground"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="ground",
            summary=route_desc[:60],
            description=f"{route_desc}. Departs in ~2 hours. Provider: {provider}.",
            details_json={
                "mode": mode,
                "route": route_desc,
                "departure": ground_dep.isoformat(),
                "arrival": ground_arr.isoformat(),
                "provider": provider,
            },
            available=True,
            estimated_arrival=ground_arr,
        ))
        return opt_id

    @staticmethod
    def _parse_duration_hours(duration_str: str) -> int:
        """Extract hours from a duration string like '3h', '3 hours', '3h 30m'.

        Falls back to 3 hours if parsing fails.
        """
        import re

        match = re.search(r"(\d+)", duration_str)
        if match:
            return int(match.group(1))
        return 3

    def _add_premium_ground(
        self,
        session: AsyncSession,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        ground_dep = base_time + timedelta(minutes=30)

        if loyalty_tier == LoyaltyTier.HON_CIRCLE:
            mode_label = "Limousine"
            cost_note = "Complimentary — airline covers full cost."
            mode = "taxi"
        else:
            mode_label = "Taxi"
            cost_note = "Taxi voucher provided."
            mode = "taxi"

        # Also check if a train route is available as an alternative
        train_routes = _GROUND_ROUTES.get(destination)
        if train_routes:
            hours = train_routes[0][2]
        else:
            hours = 3  # Estimate

        ground_arr = ground_dep + timedelta(hours=hours)
        route_desc = f"{mode_label} to {destination}"

        opt_id = f"opt-{passenger_id}-ground"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="ground",
            summary=f"{mode_label} to {destination}",
            description=f"{route_desc}. {cost_note} Ready in ~30 minutes.",
            details_json={
                "mode": mode,
                "route": route_desc,
                "departure": ground_dep.isoformat(),
                "arrival": ground_arr.isoformat(),
                "provider": mode_label,
            },
            available=True,
            estimated_arrival=ground_arr,
        ))
        return opt_id

    # ------------------------------------------------------------------
    # Alt-airport routing
    # ------------------------------------------------------------------

    def _add_alt_airport_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        dest = destination.upper().strip()

        # HON Circle gets extended routing options
        routes: list[dict[str, str | int]] = []
        if loyalty_tier == LoyaltyTier.HON_CIRCLE:
            routes.extend(_ALT_AIRPORT_ROUTES_HON.get(dest, []))
        routes.extend(_ALT_AIRPORT_ROUTES.get(dest, []))

        if not routes:
            return None

        route = routes[0]
        dep = base_time + timedelta(hours=2)
        arr = dep + timedelta(hours=int(route["total_hours"]))

        opt_id = f"opt-{passenger_id}-alt_airport"
        via = str(route["via"])
        flight = str(route["flight"])
        transfer = str(route["transfer"])
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="alt_airport",
            summary=f"Via {via} on {flight}",
            description=(
                f"Fly to {via}, then {transfer} to {dest}. "
                f"Flight {flight} departs in ~2 hours."
            ),
            details_json={
                "via_airport": via,
                "connecting_flight": flight,
                "transfer_mode": transfer,
                "total_arrival": arr.isoformat(),
            },
            available=True,
            estimated_arrival=arr,
        ))
        return opt_id

    # ------------------------------------------------------------------
    # Lounge access
    # ------------------------------------------------------------------

    async def _add_lounge_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        base_time: datetime,
        svc: ServiceLevel,
        airport: str,
    ) -> str | None:
        if svc.lounge_access == "none":
            return None

        # Try LH Lounge API for live data
        lh_lounge = await self._fetch_lh_lounge(airport, svc.lounge_access)
        if lh_lounge:
            return self._create_lounge_option_from_lh(
                session, passenger_id, base_time, svc, lh_lounge,
            )

        # Fallback to static lounge data
        airport_lounges = _LOUNGES.get(airport, {})
        tier_lounges = airport_lounges.get(svc.lounge_access, [])

        # Also include lower-tier lounges (Senator can access Business too)
        if svc.lounge_access == "first_class":
            tier_lounges = (
                airport_lounges.get("first_class", [])
                + airport_lounges.get("senator", [])
                + airport_lounges.get("business", [])
            )
        elif svc.lounge_access == "senator":
            tier_lounges = (
                airport_lounges.get("senator", [])
                + airport_lounges.get("business", [])
            )

        if not tier_lounges:
            return None

        # Pick the best available lounge (first in the list = highest tier)
        lounge = tier_lounges[0]

        opt_id = f"opt-{passenger_id}-lounge"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="lounge",
            summary=f"{lounge['name']} ({lounge['terminal']})",
            description=(
                f"Complimentary access to {lounge['name']}. "
                f"{lounge['terminal']}, {lounge['location']}. "
                f"{'Showers and sleeping rooms available. ' if lounge.get('sleeping_rooms') else ''}"
                f"{'Shower facilities available. ' if lounge.get('shower_available') and not lounge.get('sleeping_rooms') else ''}"
                f"Open {lounge['opening_hours']}."
            ),
            details_json={
                "lounge_name": lounge["name"],
                "terminal": lounge["terminal"],
                "location": lounge["location"],
                "access_type": svc.lounge_access,
                "amenities": lounge["amenities"],
                "opening_hours": lounge["opening_hours"],
                "shower_available": lounge.get("shower_available", False),
                "sleeping_rooms": lounge.get("sleeping_rooms", False),
                "source": "static",
            },
            available=True,
            estimated_arrival=base_time,  # Immediate access
        ))
        return opt_id

    async def _fetch_lh_lounge(
        self,
        airport: str,
        lounge_access: str,
    ) -> dict | None:
        """Fetch lounge data from LH API, returning the best matching lounge.

        Returns a normalized lounge dict or None on failure / unavailability.
        """
        if self.lh_client is None:
            return None

        tier_code = _TIER_CODE_MAP.get(lounge_access)
        if not tier_code:
            return None

        try:
            data = await self.lh_client.get_lounges(airport, tier_code=tier_code)
        except Exception:
            log.exception("LH Lounge API failed for %s (tier=%s)", airport, tier_code)
            return None

        try:
            lounges_container = data.get("LoungeResource", {}).get("Lounges", {})
            lounges = lounges_container.get("Lounge", [])
            if isinstance(lounges, dict):
                lounges = [lounges]  # Single result comes as dict

            if not lounges:
                return None

            lh_lounge = lounges[0]

            # Extract name (prefer English)
            names = lh_lounge.get("Names", {}).get("Name", [])
            if isinstance(names, dict):
                names = [names]
            name = next(
                (n.get("$", "") for n in names if n.get("@LanguageCode") == "en"),
                names[0].get("$", "Lufthansa Lounge") if names else "Lufthansa Lounge",
            )

            # Extract location
            locations = lh_lounge.get("Locations", {}).get("Location", [])
            if isinstance(locations, dict):
                locations = [locations]
            location = next(
                (loc.get("$", "") for loc in locations if loc.get("@LanguageCode") == "en"),
                locations[0].get("$", "") if locations else "",
            )

            # Extract opening hours
            hours_list = lh_lounge.get("OpeningHours", {}).get("OpeningHour", [])
            if isinstance(hours_list, dict):
                hours_list = [hours_list]
            opening_hours = next(
                (h.get("$", "") for h in hours_list if h.get("@LanguageCode") == "en"),
                hours_list[0].get("$", "") if hours_list else "",
            )

            # Extract features
            features = lh_lounge.get("Features", {})
            has_showers = features.get("ShowerFacilities", "").lower() == "true"
            has_sleeping = features.get("RelaxingRooms", "").lower() == "true"
            has_meeting = features.get("MeetingRooms", "").lower() == "true"

            amenities = []
            if has_showers:
                amenities.append("Shower facilities")
            if has_sleeping:
                amenities.append("Relaxing rooms")
            if has_meeting:
                amenities.append("Meeting rooms")

            log.info("LH API returned lounge '%s' at %s", name, airport)

            return {
                "name": name,
                "terminal": airport,
                "location": location,
                "amenities": amenities,
                "opening_hours": opening_hours,
                "shower_available": has_showers,
                "sleeping_rooms": has_sleeping,
            }
        except Exception:
            log.exception("Failed to parse LH Lounge response for %s", airport)
            return None

    @staticmethod
    def _create_lounge_option_from_lh(
        session: AsyncSession,
        passenger_id: str,
        base_time: datetime,
        svc: ServiceLevel,
        lounge: dict,
    ) -> str:
        """Create a lounge option row from LH API-sourced data."""
        opt_id = f"opt-{passenger_id}-lounge"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="lounge",
            summary=f"{lounge['name']} ({lounge['location'][:40]})" if lounge['location'] else lounge['name'],
            description=(
                f"Complimentary access to {lounge['name']}. "
                f"{lounge['location']}. "
                f"{'Showers and sleeping rooms available. ' if lounge.get('sleeping_rooms') else ''}"
                f"{'Shower facilities available. ' if lounge.get('shower_available') and not lounge.get('sleeping_rooms') else ''}"
                f"Open {lounge['opening_hours']}."
                if lounge['opening_hours'] else
                f"Complimentary access to {lounge['name']}. {lounge['location']}."
            ),
            details_json={
                "lounge_name": lounge["name"],
                "terminal": lounge["terminal"],
                "location": lounge["location"],
                "access_type": svc.lounge_access,
                "amenities": lounge["amenities"],
                "opening_hours": lounge["opening_hours"],
                "shower_available": lounge.get("shower_available", False),
                "sleeping_rooms": lounge.get("sleeping_rooms", False),
                "source": "lufthansa_api",
            },
            available=True,
            estimated_arrival=base_time,
        ))
        return opt_id

    # ------------------------------------------------------------------
    # Meal voucher
    # ------------------------------------------------------------------

    def _add_voucher_option(
        self,
        session: AsyncSession,
        passenger_id: str,
        base_time: datetime,
        svc: ServiceLevel,
        airport: str,
    ) -> str | None:
        if svc.meal_voucher_eur <= 0:
            return None  # Lounge access covers meals

        restaurants = _MEAL_VOUCHER_RESTAURANTS.get(airport, ["Airport restaurants"])
        valid_until = base_time + timedelta(hours=24)

        opt_id = f"opt-{passenger_id}-voucher"
        session.add(OptionRow(
            id=opt_id,
            passenger_id=passenger_id,
            type="voucher",
            summary=f"Meal voucher €{svc.meal_voucher_eur}",
            description=(
                f"€{svc.meal_voucher_eur} meal voucher for airport restaurants. "
                f"Valid for 24 hours. Redeemable at {', '.join(restaurants[:3])} and more."
            ),
            details_json={
                "voucher_type": "meal",
                "amount_eur": svc.meal_voucher_eur,
                "valid_until": valid_until.isoformat(),
                "accepted_at": restaurants,
            },
            available=True,
            estimated_arrival=base_time,  # Immediate
        ))
        return opt_id
