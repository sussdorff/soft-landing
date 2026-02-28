"""Scenario 1: Aircraft Diversion — LH456 MUC->FRA diverts to NUE (Nuremberg).

30 passengers on board, ~80% connecting through FRA to intercontinental destinations.
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
from app.seeds.passengers import compute_priority, pick_passengers

# Intercontinental connections ex-FRA
FRA_CONNECTIONS = [
    ("LH400", "FRA", "JFK", timedelta(hours=8, minutes=45)),
    ("LH710", "FRA", "NRT", timedelta(hours=11, minutes=30)),
    ("LH452", "FRA", "ORD", timedelta(hours=9, minutes=50)),
    ("LH760", "FRA", "ICN", timedelta(hours=10, minutes=40)),
    ("LH778", "FRA", "PVG", timedelta(hours=10, minutes=55)),
    ("LH498", "FRA", "MEX", timedelta(hours=11, minutes=20)),
    ("LH590", "FRA", "BOM", timedelta(hours=8, minutes=15)),
    ("LH592", "FRA", "DEL", timedelta(hours=7, minutes=45)),
    ("LH502", "FRA", "SFO", timedelta(hours=11, minutes=30)),
    ("LH794", "FRA", "SIN", timedelta(hours=12, minutes=10)),
]

PAX_COUNT = 30
DISRUPTION_ID = "dis-diversion-001"

# Fixed profile distribution (30 pax):
# 1 HON (Business C), 3 Senator (2 Business J/D, 1 Eco Y),
# 5 FTL (1 Business Z, 4 Eco Y/H/K), 21 No Status (3 full Y/B, 18 discounted)
_DIVERSION_PROFILES: list[tuple[str, str]] = [
    ("hon", "C"),
    ("sen", "J"), ("sen", "D"), ("sen", "Y"),
    ("ftl", "Z"), ("ftl", "Y"), ("ftl", "H"), ("ftl", "K"), ("ftl", "Y"),
    ("none", "Y"), ("none", "B"), ("none", "Y"),
    ("none", "M"), ("none", "L"), ("none", "T"), ("none", "V"),
    ("none", "W"), ("none", "Q"), ("none", "M"), ("none", "L"),
    ("none", "T"), ("none", "V"), ("none", "W"), ("none", "Q"),
    ("none", "M"), ("none", "L"), ("none", "T"), ("none", "V"),
    ("none", "W"), ("none", "Q"),
]
assert len(_DIVERSION_PROFILES) == PAX_COUNT


async def seed(session: AsyncSession) -> str:
    rng = random.Random(42)
    base = datetime.now(tz=UTC)
    departure = base - timedelta(hours=0, minutes=30)  # Flight already airborne
    divert_time = base  # Diversion happening now

    disruption = DisruptionRow(
        id=DISRUPTION_ID,
        type="diversion",
        flight_number="LH456",
        origin="MUC",
        destination="FRA",
        reason="Aircraft hydraulic system warning -- precautionary diversion to NUE",
        explanation=(
            "Flight LH456 from Munich to Frankfurt has diverted to Nuremberg (NUE) "
            "due to a hydraulic system warning indicator. All passengers are safe. "
            "The aircraft is being inspected. Alternative transportation is being arranged."
        ),
        detected_at=divert_time,
    )
    session.add(disruption)

    # Shuffle the fixed profiles for variety
    flight_profiles = list(_DIVERSION_PROFILES)
    rng.shuffle(flight_profiles)

    passengers = pick_passengers(
        PAX_COUNT,
        start_index=150,  # start at 151 to avoid ID overlap
        profile_distribution=flight_profiles,
        rng=rng,
    )

    for pid, name, bref, loyalty_tier, booking_class in passengers:
        has_connection = rng.random() < 0.8
        priority = compute_priority(loyalty_tier, booking_class)

        pax_row = PassengerRow(
            id=pid,
            name=name,
            booking_ref=bref,
            status="notified",
            priority=priority,
            loyalty_tier=loyalty_tier,
            booking_class=booking_class,
        )
        session.add(pax_row)

        # Segment 1: MUC->FRA (diverted to NUE)
        seg1 = SegmentRow(
            passenger_id=pid,
            flight_number="LH456",
            origin="MUC",
            destination="FRA",
            departure=departure,
            arrival=departure + timedelta(hours=1, minutes=5),
            position=0,
        )
        session.add(seg1)

        # Onward connection through FRA (80% of passengers)
        if has_connection:
            conn = rng.choice(FRA_CONNECTIONS)
            conn_depart = departure + timedelta(hours=2, minutes=30)
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

        session.add(DisruptionPassengerRow(
            disruption_id=DISRUPTION_ID, passenger_id=pid,
        ))

        _add_options(session, pid, base, has_connection)

    await session.commit()
    return DISRUPTION_ID


def _add_options(
    session: AsyncSession,
    passenger_id: str,
    base: datetime,
    has_connection: bool,
) -> None:
    # 1. Bus NUE -> FRA (~3h)
    bus_dep = base + timedelta(hours=1)
    session.add(OptionRow(
        id=f"opt-{passenger_id}-bus",
        passenger_id=passenger_id,
        type="ground",
        summary="Bus NUE -> Frankfurt Airport",
        description="Chartered bus from Nuremberg Airport to Frankfurt Airport. Departs in ~1 hour.",
        details_json={
            "mode": "bus",
            "route": "NUE Airport -> A3 Autobahn -> FRA Airport",
            "departure": bus_dep.isoformat(),
            "arrival": (bus_dep + timedelta(hours=3)).isoformat(),
            "provider": "Lufthansa Ground Services",
        },
        available=True,
        estimated_arrival=bus_dep + timedelta(hours=3),
    ))

    # 2. Train NUE -> FRA (~2h15)
    train_dep = base + timedelta(hours=1, minutes=30)
    session.add(OptionRow(
        id=f"opt-{passenger_id}-train",
        passenger_id=passenger_id,
        type="ground",
        summary="ICE train Nuremberg -> Frankfurt",
        description="ICE from Nurnberg Hbf to Frankfurt Flughafen Fernbahnhof. Shuttle from NUE to Nurnberg Hbf included.",
        details_json={
            "mode": "train",
            "route": "NUE -> Nurnberg Hbf -> ICE -> Frankfurt Flughafen Fernbf",
            "departure": train_dep.isoformat(),
            "arrival": (train_dep + timedelta(hours=2, minutes=15)).isoformat(),
            "provider": "Deutsche Bahn (Lufthansa Rail&Fly)",
        },
        available=True,
        estimated_arrival=train_dep + timedelta(hours=2, minutes=15),
    ))

    # 3. Rebook via NUE direct (limited NUE schedule)
    next_day = base + timedelta(days=1)
    session.add(OptionRow(
        id=f"opt-{passenger_id}-rebook",
        passenger_id=passenger_id,
        type="rebook",
        summary="Rebook LH191 NUE->FRA tomorrow 07:00",
        description="Next available Lufthansa flight from Nuremberg to Frankfurt tomorrow morning.",
        details_json={
            "flight_number": "LH191",
            "origin": "NUE",
            "destination": "FRA",
            "departure": next_day.replace(hour=7, minute=0, second=0, microsecond=0).isoformat(),
            "seat_available": True,
        },
        available=True,
        estimated_arrival=next_day.replace(hour=8, minute=0, second=0, microsecond=0),
    ))

    # 4. Hotel in Nuremberg overnight
    session.add(OptionRow(
        id=f"opt-{passenger_id}-hotel",
        passenger_id=passenger_id,
        type="hotel",
        summary="Hotel Nurnberg + LH191 tomorrow",
        description="Overnight stay at Movenpick Hotel Nurnberg Airport. Flight LH191 NUE->FRA at 07:00 tomorrow.",
        details_json={
            "hotel_name": "Movenpick Hotel Nurnberg Airport",
            "address": "Flughafenstr. 100, 90411 Nurnberg",
            "location": {"lat": 49.4987, "lng": 11.0668},
            "next_flight_number": "LH191",
            "next_flight_departure": next_day.replace(hour=7, minute=0, second=0, microsecond=0).isoformat(),
        },
        available=True,
        estimated_arrival=next_day.replace(hour=8, minute=0, second=0, microsecond=0),
    ))
