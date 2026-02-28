"""In-memory data store with pre-seeded Munich snowstorm scenario."""

from datetime import UTC, datetime, timedelta

from app.models import (
    AltAirportDetails,
    Disruption,
    DisruptionType,
    GroundMode,
    GroundTransportDetails,
    HotelDetails,
    Option,
    OptionType,
    Passenger,
    PassengerStatus,
    RebookDetails,
    Segment,
    TransferMode,
    Wish,
)

# --- Global stores ---
disruptions: dict[str, Disruption] = {}
passengers: dict[str, Passenger] = {}
options: dict[str, list[Option]] = {}  # keyed by passenger_id
wishes: dict[str, Wish] = {}


def _now() -> datetime:
    return datetime.now(tz=UTC)


def seed_munich_snowstorm() -> str:
    """Seed Scenario 2: Munich snowstorm cancels LH1834 MUC->CDG.

    Returns the disruption ID.
    """
    base = _now()
    departure = base + timedelta(hours=2)

    # Passengers with connecting flights through MUC
    pax_data = [
        ("pax-001", "Elena Richter", "BK7291", 5, [
            Segment(flight_number="LH1834", origin="MUC", destination="CDG",
                    departure=departure, arrival=departure + timedelta(hours=1, minutes=45)),
            Segment(flight_number="AF1580", origin="CDG", destination="JFK",
                    departure=departure + timedelta(hours=4), arrival=departure + timedelta(hours=12)),
        ]),
        ("pax-002", "Marco Bianchi", "BK4503", 3, [
            Segment(flight_number="LH1834", origin="MUC", destination="CDG",
                    departure=departure, arrival=departure + timedelta(hours=1, minutes=45)),
        ]),
        ("pax-003", "Yuki Tanaka", "BK8817", 4, [
            Segment(flight_number="LH1834", origin="MUC", destination="CDG",
                    departure=departure, arrival=departure + timedelta(hours=1, minutes=45)),
            Segment(flight_number="AF990", origin="CDG", destination="NRT",
                    departure=departure + timedelta(hours=5), arrival=departure + timedelta(hours=17)),
        ]),
        ("pax-004", "Sarah Hoffmann", "BK2156", 2, [
            Segment(flight_number="LH1834", origin="MUC", destination="CDG",
                    departure=departure, arrival=departure + timedelta(hours=1, minutes=45)),
        ]),
        ("pax-005", "James O'Connor", "BK6734", 1, [
            Segment(flight_number="LH1834", origin="MUC", destination="CDG",
                    departure=departure, arrival=departure + timedelta(hours=1, minutes=45)),
            Segment(flight_number="AF1280", origin="CDG", destination="LAX",
                    departure=departure + timedelta(hours=6), arrival=departure + timedelta(hours=18)),
        ]),
    ]

    passenger_ids = []
    for pid, name, bref, priority, itinerary in pax_data:
        pax = Passenger(
            id=pid, name=name, booking_ref=bref,
            original_itinerary=itinerary,
            status=PassengerStatus.NOTIFIED, priority=priority,
        )
        passengers[pid] = pax
        passenger_ids.append(pid)

    disruption = Disruption(
        id="dis-001",
        type=DisruptionType.CANCELLATION,
        flight_number="LH1834",
        origin="MUC",
        destination="CDG",
        reason="Heavy snowstorm in Munich — runway closures",
        explanation="Due to severe weather conditions at Munich Airport, flight LH1834 to Paris CDG has been cancelled. All runways are currently closed with expected reopening in 6-8 hours.",
        detected_at=base,
        affected_passenger_ids=passenger_ids,
    )
    disruptions[disruption.id] = disruption

    # Build options per passenger
    next_day = base + timedelta(days=1)

    for pid in passenger_ids:
        pax_options = [
            Option(
                id=f"opt-{pid}-rebook",
                type=OptionType.REBOOK,
                summary="Next available flight LH1836 tomorrow morning",
                description="Rebook to LH1836 departing MUC 07:15 tomorrow, arriving CDG 09:00.",
                details=RebookDetails(
                    flight_number="LH1836",
                    origin="MUC", destination="CDG",
                    departure=next_day.replace(hour=7, minute=15),
                    seat_available=True,
                ),
                available=True,
                estimated_arrival=next_day.replace(hour=9, minute=0),
            ),
            Option(
                id=f"opt-{pid}-hotel",
                type=OptionType.HOTEL,
                summary="Overnight at Hilton Munich Airport",
                description="Complimentary stay at Hilton Munich Airport with breakfast. Next flight LH1836 at 07:15.",
                details=HotelDetails(
                    hotel_name="Hilton Munich Airport",
                    address="Terminalstr. Mitte 20, 85356 Munich Airport",
                    location={"lat": 48.3537, "lng": 11.7750},
                    next_flight_number="LH1836",
                    next_flight_departure=next_day.replace(hour=7, minute=15),
                ),
                available=True,
                estimated_arrival=next_day.replace(hour=9, minute=0),
            ),
            Option(
                id=f"opt-{pid}-ground",
                type=OptionType.GROUND,
                summary="ICE train Munich Hbf to Paris Gare de l'Est",
                description="High-speed train via Stuttgart and Strasbourg. Departs Munich Hbf at 14:30 today.",
                details=GroundTransportDetails(
                    mode=GroundMode.TRAIN,
                    route="Munich Hbf → Stuttgart → Strasbourg → Paris Gare de l'Est",
                    departure=base + timedelta(hours=3),
                    arrival=base + timedelta(hours=9),
                    provider="Deutsche Bahn / SNCF",
                ),
                available=True,
                estimated_arrival=base + timedelta(hours=9),
            ),
            Option(
                id=f"opt-{pid}-alt",
                type=OptionType.ALT_AIRPORT,
                summary="Fly via Frankfurt (FRA) to Paris",
                description="Train to Nuremberg, then LH978 NUE→FRA, then LH1052 FRA→CDG.",
                details=AltAirportDetails(
                    via_airport="FRA",
                    connecting_flight="LH1052",
                    transfer_mode=TransferMode.TRAIN,
                    total_arrival=base + timedelta(hours=8),
                ),
                available=True,
                estimated_arrival=base + timedelta(hours=8),
            ),
        ]
        options[pid] = pax_options

    return disruption.id


def reset() -> None:
    """Clear all stores."""
    disruptions.clear()
    passengers.clear()
    options.clear()
    wishes.clear()
