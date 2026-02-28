"""Scenario 2: Munich Hub Disruption — heavy snowstorm closes all MUC runways.

6 cancelled flights, ~25 passengers each = 150 total.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
)
from app.seeds.passengers import pick_passengers

# Cancelled flights departing MUC
CANCELLED_FLIGHTS = [
    ("LH1834", "MUC", "CDG", timedelta(hours=1, minutes=45)),
    ("LH1832", "MUC", "CDG", timedelta(hours=1, minutes=45)),
    ("LH456", "MUC", "FRA", timedelta(hours=1, minutes=5)),
    ("LH2030", "MUC", "FCO", timedelta(hours=1, minutes=40)),
    ("LH1856", "MUC", "BCN", timedelta(hours=2, minutes=15)),
    ("LH1610", "MUC", "ZRH", timedelta(hours=0, minutes=55)),
]

# Realistic onward connections from each destination
ONWARD_CONNECTIONS = {
    "CDG": [
        ("AF1580", "CDG", "JFK", timedelta(hours=8, minutes=30)),
        ("AF990", "CDG", "NRT", timedelta(hours=11, minutes=45)),
        ("AF1280", "CDG", "LAX", timedelta(hours=11, minutes=15)),
        ("AF258", "CDG", "SIN", timedelta(hours=12, minutes=20)),
        ("AF382", "CDG", "GRU", timedelta(hours=11, minutes=30)),
    ],
    "FRA": [
        ("LH400", "FRA", "JFK", timedelta(hours=8, minutes=45)),
        ("LH710", "FRA", "NRT", timedelta(hours=11, minutes=30)),
        ("LH452", "FRA", "ORD", timedelta(hours=9, minutes=50)),
        ("LH760", "FRA", "ICN", timedelta(hours=10, minutes=40)),
    ],
    "FCO": [
        ("AZ608", "FCO", "JFK", timedelta(hours=9, minutes=30)),
        ("AZ780", "FCO", "NRT", timedelta(hours=12)),
        ("AZ326", "FCO", "GRU", timedelta(hours=12, minutes=15)),
    ],
    "BCN": [
        ("IB6251", "BCN", "MIA", timedelta(hours=9, minutes=45)),
        ("IB6015", "BCN", "EZE", timedelta(hours=12, minutes=30)),
        ("VY8700", "BCN", "BOG", timedelta(hours=10, minutes=40)),
    ],
    "ZRH": [
        ("LX40", "ZRH", "JFK", timedelta(hours=9)),
        ("LX16", "ZRH", "SFO", timedelta(hours=11, minutes=40)),
        ("LX180", "ZRH", "BKK", timedelta(hours=10, minutes=50)),
    ],
}

# Hotels near MUC
HOTELS = [
    ("Hilton Munich Airport", "Terminalstr. Mitte 20, 85356 Munich Airport", 48.3537, 11.7750),
    ("Marriott Munich Airport", "Alois-Steinecker-Str. 20, 85354 Freising", 48.3989, 11.7411),
    ("NH München Airport", "Lohstr. 21, 85445 Oberding", 48.3274, 11.8136),
    ("Novotel München Airport", "Nordallee 29, 85356 Munich Airport", 48.3549, 11.7712),
]

# Rebook flights (next day)
REBOOK_OPTIONS = {
    "CDG": [("LH1836", "MUC", "CDG", "07:15", "09:00"), ("LH1838", "MUC", "CDG", "11:30", "13:15")],
    "FRA": [("LH98", "MUC", "FRA", "06:30", "07:35"), ("LH100", "MUC", "FRA", "08:00", "09:05")],
    "FCO": [("LH2032", "MUC", "FCO", "07:45", "09:25"), ("LH2034", "MUC", "FCO", "12:00", "13:40")],
    "BCN": [("LH1858", "MUC", "BCN", "08:00", "10:15"), ("LH1860", "MUC", "BCN", "14:00", "16:15")],
    "ZRH": [("LH1612", "MUC", "ZRH", "06:45", "07:40"), ("LH1614", "MUC", "ZRH", "09:15", "10:10")],
}

# Ground transport alternatives
GROUND_OPTIONS = {
    "CDG": ("ICE train Munich Hbf → Paris Gare de l'Est", "Deutsche Bahn / SNCF", timedelta(hours=6)),
    "FRA": ("ICE train Munich Hbf → Frankfurt Hbf", "Deutsche Bahn", timedelta(hours=3, minutes=15)),
    "FCO": None,  # No sensible ground option to Rome
    "BCN": None,  # No sensible ground option to Barcelona
    "ZRH": ("EC train Munich Hbf → Zürich HB", "Deutsche Bahn / SBB", timedelta(hours=3, minutes=45)),
}

# Alt airport routing
ALT_AIRPORTS = {
    "CDG": ("FRA", "LH1052", "train", timedelta(hours=7)),
    "FRA": ("NUE", "LH190", "bus", timedelta(hours=4, minutes=30)),
    "FCO": ("FRA", "LH234", "train", timedelta(hours=6, minutes=30)),
    "BCN": ("FRA", "LH1126", "train", timedelta(hours=7)),
    "ZRH": ("NUE", "LX1191", "bus", timedelta(hours=3, minutes=45)),
}

PAX_PER_FLIGHT = 25
DISRUPTION_ID = "dis-snowstorm-001"


async def seed(session: AsyncSession) -> str:
    base = datetime.now(tz=UTC)
    pax_counter = 0

    disruption = DisruptionRow(
        id=DISRUPTION_ID,
        type="cancellation",
        flight_number="MUC-HUB",
        origin="MUC",
        destination="ALL",
        reason="Heavy snowstorm in Munich — all runways closed",
        explanation=(
            "Due to a severe snowstorm at Munich Airport, all runways are closed "
            "and 6 departing flights have been cancelled. Estimated reopening in 6-8 hours. "
            "Affected routes: CDG (2x), FRA, FCO, BCN, ZRH."
        ),
        detected_at=base,
    )
    session.add(disruption)

    for flight_idx, (flight_num, origin, dest, flight_dur) in enumerate(CANCELLED_FLIGHTS):
        departure = base + timedelta(hours=1 + flight_idx * 0.5)
        passengers = pick_passengers(PAX_PER_FLIGHT, start_index=pax_counter)
        pax_counter += PAX_PER_FLIGHT

        for pid, name, bref in passengers:
            has_connection = random.random() < 0.6
            pax_row = PassengerRow(
                id=pid,
                name=name,
                booking_ref=bref,
                status="notified",
                priority=random.randint(1, 5),
            )
            session.add(pax_row)

            # First segment: the cancelled MUC flight
            seg1 = SegmentRow(
                passenger_id=pid,
                flight_number=flight_num,
                origin=origin,
                destination=dest,
                departure=departure,
                arrival=departure + flight_dur,
                position=0,
            )
            session.add(seg1)

            # Onward connection (60% of passengers)
            if has_connection and dest in ONWARD_CONNECTIONS:
                conn = random.choice(ONWARD_CONNECTIONS[dest])
                conn_depart = departure + flight_dur + timedelta(hours=random.uniform(2, 4))
                seg2 = SegmentRow(
                    passenger_id=pid,
                    flight_number=conn[0],
                    origin=conn[1],
                    destination=conn[2],
                    departure=conn_depart,
                    arrival=conn_depart + conn[3],
                    position=1,
                )
                session.add(seg2)

            # Link passenger to disruption
            session.add(DisruptionPassengerRow(
                disruption_id=DISRUPTION_ID, passenger_id=pid,
            ))

            # Generate 4 options per passenger
            _add_options(session, pid, dest, base, departure)

    await session.commit()
    return DISRUPTION_ID


def _add_options(
    session: AsyncSession,
    passenger_id: str,
    dest: str,
    base: datetime,
    departure: datetime,
) -> None:
    next_day = base + timedelta(days=1)
    hotel = random.choice(HOTELS)

    # 1. Rebook
    if dest in REBOOK_OPTIONS:
        rb = random.choice(REBOOK_OPTIONS[dest])
        rb_dep_h, rb_dep_m = map(int, rb[3].split(":"))
        rb_arr_h, rb_arr_m = map(int, rb[4].split(":"))
        rb_departure = next_day.replace(hour=rb_dep_h, minute=rb_dep_m, second=0, microsecond=0)
        rb_arrival = next_day.replace(hour=rb_arr_h, minute=rb_arr_m, second=0, microsecond=0)

        session.add(OptionRow(
            id=f"opt-{passenger_id}-rebook",
            passenger_id=passenger_id,
            type="rebook",
            summary=f"Rebook to {rb[0]} tomorrow {rb[3]}",
            description=f"Rebook to {rb[0]} departing {rb[1]} {rb[3]} → {rb[2]} {rb[4]} tomorrow.",
            details_json={
                "flight_number": rb[0], "origin": rb[1], "destination": rb[2],
                "departure": rb_departure.isoformat(), "seat_available": True,
            },
            available=True,
            estimated_arrival=rb_arrival,
        ))

    # 2. Hotel
    session.add(OptionRow(
        id=f"opt-{passenger_id}-hotel",
        passenger_id=passenger_id,
        type="hotel",
        summary=f"Overnight at {hotel[0]}",
        description=f"Complimentary stay at {hotel[0]} with breakfast. Next flight tomorrow morning.",
        details_json={
            "hotel_name": hotel[0], "address": hotel[1],
            "location": {"lat": hotel[2], "lng": hotel[3]},
            "next_flight_number": REBOOK_OPTIONS.get(dest, [("LH9999", "MUC", dest, "08:00", "10:00")])[0][0],
            "next_flight_departure": next_day.replace(hour=7, minute=0, second=0, microsecond=0).isoformat(),
        },
        available=True,
        estimated_arrival=next_day.replace(hour=10, minute=0, second=0, microsecond=0),
    ))

    # 3. Ground transport (if available for this destination)
    ground = GROUND_OPTIONS.get(dest)
    if ground:
        route, provider, duration = ground
        ground_dep = base + timedelta(hours=2)
        session.add(OptionRow(
            id=f"opt-{passenger_id}-ground",
            passenger_id=passenger_id,
            type="ground",
            summary=route[:60],
            description=f"{route}. Departs in ~2 hours.",
            details_json={
                "mode": "train", "route": route,
                "departure": ground_dep.isoformat(),
                "arrival": (ground_dep + duration).isoformat(),
                "provider": provider,
            },
            available=True,
            estimated_arrival=ground_dep + duration,
        ))

    # 4. Alt airport
    if dest in ALT_AIRPORTS:
        via, conn_flight, transfer, total_dur = ALT_AIRPORTS[dest]
        session.add(OptionRow(
            id=f"opt-{passenger_id}-alt",
            passenger_id=passenger_id,
            type="alt_airport",
            summary=f"Fly via {via} to {dest}",
            description=f"Transfer to {via}, then {conn_flight} {via}→{dest}.",
            details_json={
                "via_airport": via, "connecting_flight": conn_flight,
                "transfer_mode": transfer,
                "total_arrival": (base + total_dur).isoformat(),
            },
            available=True,
            estimated_arrival=base + total_dur,
        ))
