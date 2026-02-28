"""Option Generator — creates rebooking/hotel/ground/alt options for passengers.

Seed-style deterministic generation for the hackathon.
Later: wire in Gemini + LH API for live option generation.
"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import OptionRow
from app.models import DisruptionType


# Generic rebook templates by destination
_REBOOK_TEMPLATES: dict[str, list[tuple[str, str, str, int, int]]] = {
    # (flight, origin, dest, dep_hour, dep_min)
    "FRA": [("LH98", "MUC", "FRA", 6, 30), ("LH100", "MUC", "FRA", 8, 0)],
    "CDG": [("LH1836", "MUC", "CDG", 7, 15), ("LH1838", "MUC", "CDG", 11, 30)],
    "FCO": [("LH2032", "MUC", "FCO", 7, 45)],
    "BCN": [("LH1858", "MUC", "BCN", 8, 0)],
    "ZRH": [("LH1612", "MUC", "ZRH", 6, 45)],
}

_HOTELS: list[tuple[str, str, float, float]] = [
    ("Airport Hotel", "Airport Terminal Area", 48.354, 11.775),
    ("City Center Hotel", "Main Street 1", 48.137, 11.576),
]

_GROUND_ROUTES: dict[str, tuple[str, str, int]] = {
    # dest -> (route_desc, provider, hours)
    "FRA": ("ICE Munich Hbf - Frankfurt Hbf", "Deutsche Bahn", 3),
    "ZRH": ("EC Munich Hbf - Zurich HB", "Deutsche Bahn / SBB", 4),
    "CDG": ("ICE Munich Hbf - Paris Est", "Deutsche Bahn / SNCF", 6),
}


class OptionGenerator:
    """Generates travel options for disrupted passengers."""

    def generate_options(
        self,
        session: AsyncSession,
        *,
        disruption_id: str,
        passenger_id: str,
        disruption_type: DisruptionType,
        destination: str,
        base_time: datetime,
    ) -> None:
        """Add option rows to session (not yet committed).

        Options depend on disruption type:
        - CANCELLATION/DELAY: rebook, hotel, ground, alt_airport
        - DIVERSION: ground (bus/train to dest), rebook, hotel
        - GATE_CHANGE: no options needed (info only)
        """
        if disruption_type == DisruptionType.GATE_CHANGE:
            return  # Gate changes don't need rebooking options

        next_day = base_time + timedelta(days=1)

        # 1. Rebook option
        templates = _REBOOK_TEMPLATES.get(destination, [])
        if templates:
            tpl = templates[0]
            dep = next_day.replace(
                hour=tpl[3], minute=tpl[4], second=0, microsecond=0,
            )
            arr = dep + timedelta(hours=1, minutes=30)
            session.add(OptionRow(
                id=f"opt-{passenger_id}-rebook",
                passenger_id=passenger_id,
                type="rebook",
                summary=f"Rebook {tpl[0]} tomorrow {tpl[3]:02d}:{tpl[4]:02d}",
                description=f"Next available flight {tpl[0]} {tpl[1]}-{tpl[2]} tomorrow.",
                details_json={
                    "flight_number": tpl[0],
                    "origin": tpl[1],
                    "destination": tpl[2],
                    "departure": dep.isoformat(),
                    "seat_available": True,
                },
                available=True,
                estimated_arrival=arr,
            ))
        else:
            # Generic rebook for unknown destinations
            dep = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
            arr = dep + timedelta(hours=2)
            session.add(OptionRow(
                id=f"opt-{passenger_id}-rebook",
                passenger_id=passenger_id,
                type="rebook",
                summary=f"Next available flight to {destination}",
                description=f"Rebooked on next available flight to {destination} tomorrow.",
                details_json={
                    "flight_number": "LHXXXX",
                    "origin": "MUC",
                    "destination": destination,
                    "departure": dep.isoformat(),
                    "seat_available": True,
                },
                available=True,
                estimated_arrival=arr,
            ))

        # 2. Hotel option
        hotel = _HOTELS[0]
        session.add(OptionRow(
            id=f"opt-{passenger_id}-hotel",
            passenger_id=passenger_id,
            type="hotel",
            summary=f"Overnight at {hotel[0]}",
            description=f"Complimentary stay at {hotel[0]} with breakfast.",
            details_json={
                "hotel_name": hotel[0],
                "address": hotel[1],
                "location": {"lat": hotel[2], "lng": hotel[3]},
                "next_flight_number": templates[0][0] if templates else "LHXXXX",
                "next_flight_departure": next_day.replace(
                    hour=7, minute=0, second=0, microsecond=0,
                ).isoformat(),
            },
            available=True,
            estimated_arrival=next_day.replace(
                hour=10, minute=0, second=0, microsecond=0,
            ),
        ))

        # 3. Ground transport (if route exists)
        ground = _GROUND_ROUTES.get(destination)
        if ground:
            route, provider, hours = ground
            ground_dep = base_time + timedelta(hours=2)
            ground_arr = ground_dep + timedelta(hours=hours)
            session.add(OptionRow(
                id=f"opt-{passenger_id}-ground",
                passenger_id=passenger_id,
                type="ground",
                summary=route[:60],
                description=f"{route}. Departs in ~2 hours.",
                details_json={
                    "mode": "train",
                    "route": route,
                    "departure": ground_dep.isoformat(),
                    "arrival": ground_arr.isoformat(),
                    "provider": provider,
                },
                available=True,
                estimated_arrival=ground_arr,
            ))
