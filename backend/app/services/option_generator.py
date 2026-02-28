"""Option Generator — creates rebooking/hotel/ground/alt options for passengers.

Uses injected ports (FlightDataPort, GroundingPort, OptionRepository) for all
external data and persistence.  The adapter layer handles API calls vs. static
fallbacks — this module contains only business logic: which options to
generate and service-level decisions.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.adapters.static_data import (
    get_alt_airport_routes,
    get_alt_airport_routes_hon,
    get_any_airline_flights,
    get_meal_voucher_restaurants,
    get_star_alliance_flights,
)
from app.models import (
    BookingClass,
    DisruptionType,
    LoyaltyTier,
)
from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.ports.repositories import OptionRepository
from app.models import compute_service_level

if TYPE_CHECKING:
    from app.models import ServiceLevel
    from app.services.gemini import HotelOption

log = logging.getLogger(__name__)


class OptionGenerator:
    """Generates travel options for disrupted passengers.

    All external data (flights, hotels, transport, lounges) is fetched
    through injected port interfaces.  Persistence goes through the
    OptionRepository port.
    """

    def __init__(
        self,
        flight_data: FlightDataPort,
        grounding: GroundingPort,
        option_repo: OptionRepository,
    ) -> None:
        self._flight_data = flight_data
        self._grounding = grounding
        self._option_repo = option_repo

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate_options(
        self,
        disruption_id: str,
        passenger_id: str,
        disruption_type: DisruptionType,
        destination: str,
        *,
        loyalty_tier: LoyaltyTier = LoyaltyTier.NONE,
        booking_class: BookingClass = BookingClass.Y,
    ) -> list[str]:
        """Generate and persist options for a disrupted passenger.

        Returns a list of the created option IDs.
        """
        if disruption_type == DisruptionType.GATE_CHANGE:
            return []  # Gate changes don't need rebooking options

        base_time = datetime.now(tz=UTC)
        svc = compute_service_level(loyalty_tier, booking_class)
        option_ids: list[str] = []

        # 1. Rebook
        opt_id = await self._add_rebook_option(
            passenger_id, destination, base_time, svc, loyalty_tier,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 2. Hotel
        opt_id = await self._add_hotel_option(
            passenger_id, destination, base_time, svc,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 3. Ground transport
        opt_id = await self._add_ground_option(
            passenger_id, destination, base_time, svc, loyalty_tier,
        )
        if opt_id:
            option_ids.append(opt_id)

        # 4. Alt-airport (cancellations / diversions only)
        if disruption_type in (DisruptionType.CANCELLATION, DisruptionType.DIVERSION):
            opt_id = await self._add_alt_airport_option(
                passenger_id, destination, base_time, loyalty_tier,
            )
            if opt_id:
                option_ids.append(opt_id)

        # 5. Lounge access (if eligible)
        opt_id = await self._add_lounge_option(
            passenger_id, base_time, svc, "MUC",
        )
        if opt_id:
            option_ids.append(opt_id)

        # 6. Meal voucher (if no lounge access)
        opt_id = await self._add_voucher_option(
            passenger_id, base_time, svc, "MUC",
        )
        if opt_id:
            option_ids.append(opt_id)

        return option_ids

    # ------------------------------------------------------------------
    # Description enrichment helper
    # ------------------------------------------------------------------

    async def _enrich_description(
        self,
        option_type: str,
        details: dict,
        fallback: str,
    ) -> str:
        """Use grounding port to generate a richer description.

        Best-effort — returns fallback on any failure.
        """
        try:
            details_str = {k: str(v) for k, v in details.items()}
            enriched = await self._grounding.describe_option(option_type, details_str)
            return enriched if enriched else fallback
        except Exception:
            log.exception("describe_option failed for %s", option_type)
            return fallback

    # ------------------------------------------------------------------
    # Rebook
    # ------------------------------------------------------------------

    async def _add_rebook_option(
        self,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        next_day = base_time + timedelta(days=1)
        dest = destination.upper().strip()
        next_day_str = next_day.strftime("%Y-%m-%d")

        # Fetch schedules through the flight data port
        candidates = self._parse_schedule_candidates(
            await self._flight_data.get_schedules("MUC", dest, next_day_str),
            "MUC", dest,
        )

        # Expand scope for Star Alliance / any-airline tiers
        if svc.rebooking_scope in ("star_alliance", "any_airline"):
            candidates.extend(get_star_alliance_flights().get(dest, []))

        if svc.rebooking_scope == "any_airline":
            candidates.extend(get_any_airline_flights().get(dest, []))

        scope_note = self._rebooking_scope_note(svc, loyalty_tier)
        upgrade_note = ""
        if svc.upgrade_eligible:
            upgrade_note = " Upgrade to higher cabin possible if available."

        if candidates:
            candidates.sort(key=lambda t: (t[3], t[4]))
            tpl = candidates[0]
            dep = next_day.replace(
                hour=tpl[3], minute=tpl[4], second=0, microsecond=0,
            )
            arr = dep + timedelta(hours=1, minutes=30)

            details_json = {
                "flight_number": tpl[0],
                "origin": tpl[1],
                "destination": tpl[2],
                "departure": dep.isoformat(),
                "seat_available": True,
            }
            fallback_desc = (
                f"Next available flight {tpl[0]} {tpl[1]}-{tpl[2]} tomorrow. "
                f"{scope_note}{upgrade_note}"
            ).strip()
            from app.models import RebookDetails
            description = await self._enrich_description("rebook", details_json, fallback_desc)

            return await self._option_repo.create_option(
                passenger_id=passenger_id,
                option_type="rebook",
                summary=f"Rebook {tpl[0]} tomorrow {tpl[3]:02d}:{tpl[4]:02d}",
                description=description,
                details=RebookDetails(**details_json),
                available=True,
                estimated_arrival=arr,
            )

        # Generic rebook for unknown destinations
        dep = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
        arr = dep + timedelta(hours=2)
        details_json = {
            "flight_number": "LHXXXX",
            "origin": "MUC",
            "destination": destination,
            "departure": dep.isoformat(),
            "seat_available": True,
        }
        fallback_desc = (
            f"Rebooked on next available flight to {destination} tomorrow. "
            f"{scope_note}"
        ).strip()
        from app.models import RebookDetails
        description = await self._enrich_description("rebook", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="rebook",
            summary=f"Next available flight to {destination}",
            description=description,
            details=RebookDetails(**details_json),
            available=True,
            estimated_arrival=arr,
        )

    @staticmethod
    def _parse_schedule_candidates(
        data: dict,
        origin: str,
        destination: str,
    ) -> list[tuple[str, str, str, int, int]]:
        """Parse ScheduleResource dict into candidate tuples.

        Returns ``[(flight_code, dep_airport, arr_airport, dep_hour, dep_minute)]``.
        """
        candidates: list[tuple[str, str, str, int, int]] = []
        try:
            schedules = data.get("ScheduleResource", {}).get("Schedule", [])
            if isinstance(schedules, dict):
                schedules = [schedules]
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
            log.exception("Failed to parse schedule response for %s->%s", origin, destination)
        return candidates

    @staticmethod
    def _rebooking_scope_note(svc: ServiceLevel, loyalty_tier: LoyaltyTier) -> str:
        if svc.rebooking_scope == "any_airline":
            return "Rebooking on any airline. Including non-Star Alliance options."
        if svc.rebooking_scope == "star_alliance":
            return "Rebooking across Star Alliance network."
        if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER:
            return "Rebooking within Lufthansa Group (LH, OS, LX, SN)."
        return "Rebooking within Lufthansa Group."

    # ------------------------------------------------------------------
    # Hotel
    # ------------------------------------------------------------------

    async def _add_hotel_option(
        self,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
    ) -> str | None:
        next_day = base_time + timedelta(days=1)
        next_flight_dep = next_day.replace(hour=7, minute=0, second=0, microsecond=0)

        hotels = await self._grounding.find_nearby_hotels("MUC")
        best = self._rank_hotels(hotels, svc)

        if best:
            name = best.name
            address = best.address
            price = self._parse_price(best.price_range, svc.hotel_budget_eur)
            rating = best.rating or ""
            maps_uri = best.maps_uri or ""
            stars = svc.hotel_stars
            lat, lng = 48.354, 11.775
        else:
            name = "Airport Hotel"
            address = "Airport Terminal Area"
            lat, lng = 48.354, 11.775
            stars = 3
            price = 80
            rating = "3.5"
            maps_uri = ""

        star_label = f"{stars}-star" if stars else ""
        budget_note = f" (up to {svc.hotel_budget_eur} EUR/night)" if svc.hotel_budget_eur else ""
        suite_note = ""
        if svc.hotel_stars >= 5:
            suite_note = " Executive Suite or Club Room included."

        details_json = {
            "hotel_name": name,
            "address": address,
            "location": {"lat": lat, "lng": lng},
            "next_flight_number": "LHXXXX",
            "next_flight_departure": next_flight_dep.isoformat(),
            "stars": stars,
            "price_per_night": price,
            "maps_uri": maps_uri,
            "rating": rating,
        }
        fallback_desc = (
            f"Complimentary {star_label} stay at {name} with breakfast."
            f"{budget_note}{' ' + suite_note if suite_note else ''}"
        ).strip()

        from app.models import HotelDetails
        description = await self._enrich_description("hotel", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="hotel",
            summary=f"Overnight at {name}",
            description=description,
            details=HotelDetails(**details_json),
            available=True,
            estimated_arrival=next_day.replace(
                hour=10, minute=0, second=0, microsecond=0,
            ),
        )

    @staticmethod
    def _rank_hotels(
        hotels: list[HotelOption],
        svc: ServiceLevel,
    ) -> HotelOption | None:
        """Pick the best hotel from results given the service level."""
        if not hotels:
            return None

        def _sort_key(h: HotelOption) -> float:
            try:
                return -float(h.rating)
            except (ValueError, TypeError):
                return 0.0

        ranked = sorted(hotels, key=_sort_key)

        if svc.hotel_stars >= 5:
            return ranked[0]
        if svc.hotel_stars >= 4:
            return ranked[min(1, len(ranked) - 1)]
        return ranked[-1]

    @staticmethod
    def _parse_price(price_range: str, fallback: int) -> int:
        """Extract a numeric price from a string like '120-180 EUR'."""
        if not price_range:
            return fallback
        numbers = re.findall(r"\d+", price_range)
        if len(numbers) >= 2:
            return (int(numbers[0]) + int(numbers[1])) // 2
        if numbers:
            return int(numbers[0])
        return fallback

    # ------------------------------------------------------------------
    # Ground transport
    # ------------------------------------------------------------------

    async def _add_ground_option(
        self,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        svc: ServiceLevel,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        dest = destination.upper().strip()

        # HON / Senator: offer taxi/limousine regardless of destination
        if svc.transport_mode in ("limousine", "taxi"):
            return await self._add_premium_ground(
                passenger_id, dest, base_time, svc, loyalty_tier,
            )

        # Standard passengers: query grounding port for transport options
        options = await self._grounding.find_ground_transport("MUC", dest)
        if options:
            best = options[0]
            ground_dep = base_time + timedelta(hours=2)
            dur_hours = self._parse_duration_hours(best.duration)
            ground_arr = ground_dep + timedelta(hours=dur_hours)

            details_json = {
                "mode": best.mode,
                "route": best.route,
                "departure": ground_dep.isoformat(),
                "arrival": ground_arr.isoformat(),
                "provider": best.provider,
            }
            fallback_desc = (
                f"{best.route}. Provider: {best.provider}. "
                f"Duration: {best.duration}."
            )
            from app.models import GroundTransportDetails
            description = await self._enrich_description("ground", details_json, fallback_desc)

            return await self._option_repo.create_option(
                passenger_id=passenger_id,
                option_type="ground",
                summary=best.route[:60] if best.route else f"{best.mode} to {dest}",
                description=description,
                details=GroundTransportDetails(**details_json),
                available=True,
                estimated_arrival=ground_arr,
            )

        return None

    @staticmethod
    def _parse_duration_hours(duration_str: str) -> int:
        """Extract hours from a duration string like '3h', '3 hours', '3h 30m'.

        Falls back to 3 hours if parsing fails.
        """
        match = re.search(r"(\d+)", duration_str)
        if match:
            return int(match.group(1))
        return 3

    async def _add_premium_ground(
        self,
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
        else:
            mode_label = "Taxi"
            cost_note = "Taxi voucher provided."

        # Check grounding port for travel time estimate
        transport = await self._grounding.find_ground_transport("MUC", destination)
        if transport:
            hours = self._parse_duration_hours(transport[0].duration)
        else:
            hours = 3

        ground_arr = ground_dep + timedelta(hours=hours)
        route_desc = f"{mode_label} to {destination}"

        details_json = {
            "mode": "taxi",
            "route": route_desc,
            "departure": ground_dep.isoformat(),
            "arrival": ground_arr.isoformat(),
            "provider": mode_label,
        }
        fallback_desc = f"{route_desc}. {cost_note} Ready in ~30 minutes."

        from app.models import GroundTransportDetails
        description = await self._enrich_description("ground", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="ground",
            summary=f"{mode_label} to {destination}",
            description=description,
            details=GroundTransportDetails(**details_json),
            available=True,
            estimated_arrival=ground_arr,
        )

    # ------------------------------------------------------------------
    # Alt-airport routing
    # ------------------------------------------------------------------

    async def _add_alt_airport_option(
        self,
        passenger_id: str,
        destination: str,
        base_time: datetime,
        loyalty_tier: LoyaltyTier,
    ) -> str | None:
        dest = destination.upper().strip()

        routes: list[dict[str, str | int]] = []
        if loyalty_tier == LoyaltyTier.HON_CIRCLE:
            routes.extend(get_alt_airport_routes_hon().get(dest, []))
        routes.extend(get_alt_airport_routes().get(dest, []))

        if not routes:
            return None

        route = routes[0]
        dep = base_time + timedelta(hours=2)
        arr = dep + timedelta(hours=int(route["total_hours"]))

        via = str(route["via"])
        flight = str(route["flight"])
        transfer = str(route["transfer"])

        details_json = {
            "via_airport": via,
            "connecting_flight": flight,
            "transfer_mode": transfer,
            "total_arrival": arr.isoformat(),
        }
        fallback_desc = (
            f"Fly to {via}, then {transfer} to {dest}. "
            f"Flight {flight} departs in ~2 hours."
        )

        from app.models import AltAirportDetails
        description = await self._enrich_description("alt_airport", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="alt_airport",
            summary=f"Via {via} on {flight}",
            description=description,
            details=AltAirportDetails(**details_json),
            available=True,
            estimated_arrival=arr,
        )

    # ------------------------------------------------------------------
    # Lounge access
    # ------------------------------------------------------------------

    async def _add_lounge_option(
        self,
        passenger_id: str,
        base_time: datetime,
        svc: ServiceLevel,
        airport: str,
    ) -> str | None:
        if svc.lounge_access == "none":
            return None

        tier_code_map = {"first_class": "HON", "senator": "SEN", "business": "FTL"}
        tier_code = tier_code_map.get(svc.lounge_access)
        if not tier_code:
            return None

        data = await self._flight_data.get_lounges(airport, tier_code=tier_code)
        lounge = self._parse_best_lounge(data, svc.lounge_access)
        if not lounge:
            return None

        details_json = {
            "lounge_name": lounge["name"],
            "terminal": lounge["terminal"],
            "location": lounge["location"],
            "access_type": svc.lounge_access,
            "amenities": lounge["amenities"],
            "opening_hours": lounge["opening_hours"],
            "shower_available": lounge.get("shower_available", False),
            "sleeping_rooms": lounge.get("sleeping_rooms", False),
        }
        fallback_desc = (
            f"Complimentary access to {lounge['name']}. "
            f"{lounge['terminal']}, {lounge['location']}. "
            f"{'Showers and sleeping rooms available. ' if lounge.get('sleeping_rooms') else ''}"
            f"{'Shower facilities available. ' if lounge.get('shower_available') and not lounge.get('sleeping_rooms') else ''}"
            f"Open {lounge['opening_hours']}."
        )

        from app.models import LoungeDetails
        description = await self._enrich_description("lounge", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="lounge",
            summary=f"{lounge['name']} ({lounge['terminal']})",
            description=description,
            details=LoungeDetails(**details_json),
            available=True,
            estimated_arrival=base_time,
        )

    @staticmethod
    def _parse_best_lounge(data: dict, lounge_access: str) -> dict | None:
        """Parse LoungeResource response and pick the best lounge."""
        if not data:
            return None

        try:
            lounges_container = data.get("LoungeResource", {}).get("Lounges", {})
            lounges = lounges_container.get("Lounge", [])
            if isinstance(lounges, dict):
                lounges = [lounges]

            if not lounges:
                return None

            lh_lounge = lounges[0]

            names = lh_lounge.get("Names", {}).get("Name", [])
            if isinstance(names, dict):
                names = [names]
            name = next(
                (n.get("$", "") for n in names if n.get("@LanguageCode") == "en"),
                names[0].get("$", "Lufthansa Lounge") if names else "Lufthansa Lounge",
            )

            locations = lh_lounge.get("Locations", {}).get("Location", [])
            if isinstance(locations, dict):
                locations = [locations]
            location = next(
                (loc.get("$", "") for loc in locations if loc.get("@LanguageCode") == "en"),
                locations[0].get("$", "") if locations else "",
            )

            hours_list = lh_lounge.get("OpeningHours", {}).get("OpeningHour", [])
            if isinstance(hours_list, dict):
                hours_list = [hours_list]
            opening_hours = next(
                (h.get("$", "") for h in hours_list if h.get("@LanguageCode") == "en"),
                hours_list[0].get("$", "") if hours_list else "",
            )

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

            return {
                "name": name,
                "terminal": lh_lounge.get("Terminal", ""),
                "location": location,
                "amenities": amenities,
                "opening_hours": opening_hours,
                "shower_available": has_showers,
                "sleeping_rooms": has_sleeping,
            }
        except Exception:
            log.exception("Failed to parse lounge response")
            return None

    # ------------------------------------------------------------------
    # Meal voucher
    # ------------------------------------------------------------------

    async def _add_voucher_option(
        self,
        passenger_id: str,
        base_time: datetime,
        svc: ServiceLevel,
        airport: str,
    ) -> str | None:
        if svc.meal_voucher_eur <= 0:
            return None  # Lounge access covers meals

        restaurants = get_meal_voucher_restaurants().get(airport, ["Airport restaurants"])
        valid_until = base_time + timedelta(hours=24)

        details_json = {
            "voucher_type": "meal",
            "amount_eur": svc.meal_voucher_eur,
            "valid_until": valid_until.isoformat(),
            "accepted_at": restaurants,
        }
        fallback_desc = (
            f"\u20ac{svc.meal_voucher_eur} meal voucher for airport restaurants. "
            f"Valid for 24 hours. Redeemable at {', '.join(restaurants[:3])} and more."
        )

        from app.models import VoucherDetails
        description = await self._enrich_description("voucher", details_json, fallback_desc)

        return await self._option_repo.create_option(
            passenger_id=passenger_id,
            option_type="voucher",
            summary=f"Meal voucher \u20ac{svc.meal_voucher_eur}",
            description=description,
            details=VoucherDetails(**details_json),
            available=True,
            estimated_arrival=base_time,  # Immediate
        )
