"""Pydantic models for the ReRoute disruption management API."""

from datetime import datetime
from enum import StrEnum, auto
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


# --- Enums ---

class DisruptionType(StrEnum):
    CANCELLATION = auto()
    DIVERSION = auto()
    DELAY = auto()
    GATE_CHANGE = auto()


class PassengerStatus(StrEnum):
    UNAFFECTED = auto()
    NOTIFIED = auto()
    CHOSE = auto()
    APPROVED = auto()
    DENIED = auto()


class OptionType(StrEnum):
    REBOOK = auto()
    HOTEL = auto()
    GROUND = auto()
    ALT_AIRPORT = auto()
    LOUNGE = auto()
    VOUCHER = auto()


class TransferMode(StrEnum):
    TRAIN = auto()
    BUS = auto()
    TAXI = auto()


class GroundMode(StrEnum):
    TRAIN = auto()
    BUS = auto()


class WishStatus(StrEnum):
    PENDING = auto()
    APPROVED = auto()
    DENIED = auto()


class LoyaltyTier(StrEnum):
    """Lufthansa Miles & More status levels."""
    NONE = "none"              # No status
    FREQUENT_TRAVELLER = "ftl"  # Star Alliance Silver
    SENATOR = "sen"            # Star Alliance Gold
    HON_CIRCLE = "hon"         # Above Gold, invitation-only


class CabinClass(StrEnum):
    """Cabin classes."""
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class BookingClass(StrEnum):
    """Lufthansa booking class codes."""
    # First
    F = "F"  # Full-fare First
    A = "A"  # Award/discounted First
    # Business
    J = "J"  # Full-fare Business
    C = "C"  # Business
    D = "D"  # Discounted Business
    Z = "Z"  # Discounted Business
    # Premium Economy
    E = "E"
    N = "N"
    P = "P"
    # Economy (full-fare)
    Y = "Y"  # Full-fare Economy
    B = "B"  # Full-fare Economy
    # Economy (mid-tier)
    H = "H"
    K = "K"
    M = "M"
    # Economy (discounted)
    L = "L"
    T = "T"
    V = "V"
    W = "W"
    Q = "Q"
    G = "G"
    S = "S"


_BOOKING_TO_CABIN: dict[BookingClass, CabinClass] = {
    BookingClass.F: CabinClass.FIRST,
    BookingClass.A: CabinClass.FIRST,
    BookingClass.J: CabinClass.BUSINESS,
    BookingClass.C: CabinClass.BUSINESS,
    BookingClass.D: CabinClass.BUSINESS,
    BookingClass.Z: CabinClass.BUSINESS,
    BookingClass.E: CabinClass.PREMIUM_ECONOMY,
    BookingClass.N: CabinClass.PREMIUM_ECONOMY,
    BookingClass.P: CabinClass.PREMIUM_ECONOMY,
    BookingClass.Y: CabinClass.ECONOMY,
    BookingClass.B: CabinClass.ECONOMY,
    BookingClass.H: CabinClass.ECONOMY,
    BookingClass.K: CabinClass.ECONOMY,
    BookingClass.M: CabinClass.ECONOMY,
    BookingClass.L: CabinClass.ECONOMY,
    BookingClass.T: CabinClass.ECONOMY,
    BookingClass.V: CabinClass.ECONOMY,
    BookingClass.W: CabinClass.ECONOMY,
    BookingClass.Q: CabinClass.ECONOMY,
    BookingClass.G: CabinClass.ECONOMY,
    BookingClass.S: CabinClass.ECONOMY,
}

# Full-fare economy booking classes (higher priority than discounted)
_FULL_FARE_ECONOMY = {BookingClass.Y, BookingClass.B}


def cabin_class_from_booking(booking_class: BookingClass) -> CabinClass:
    """Derive the cabin class from a Lufthansa booking class code."""
    return _BOOKING_TO_CABIN.get(booking_class, CabinClass.ECONOMY)


# --- Core Models ---

class Segment(CamelModel):
    flight_number: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime


type Itinerary = list[Segment]


class Disruption(CamelModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    type: DisruptionType
    flight_number: str
    origin: str
    destination: str
    reason: str
    explanation: str
    detected_at: datetime
    affected_passenger_ids: list[str] = Field(default_factory=list)


class Passenger(CamelModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str
    booking_ref: str
    original_itinerary: Itinerary
    status: PassengerStatus = PassengerStatus.UNAFFECTED
    denial_count: int = 0
    priority: int = 0
    loyalty_tier: LoyaltyTier = LoyaltyTier.NONE
    booking_class: BookingClass = BookingClass.Y
    cabin_class: CabinClass = CabinClass.ECONOMY


class ServiceLevel(CamelModel):
    """Computed service recovery parameters based on passenger profile."""
    priority_score: int  # Higher = served first
    hotel_stars: int  # 3-5
    hotel_budget_eur: int  # Per night budget
    transport_mode: str  # "limousine", "taxi", "shuttle"
    lounge_access: str  # "first_class", "senator", "business", "none"
    meal_voucher_eur: int  # 0 if lounge access, else 12-15
    rebooking_scope: str  # "any_airline", "star_alliance", "lh_group"
    upgrade_eligible: bool  # Can be rebooked to higher cabin if needed


# --- Option Detail Types ---

class RebookDetails(CamelModel):
    flight_number: str
    origin: str
    destination: str
    departure: datetime
    seat_available: bool = True


class HotelDetails(CamelModel):
    hotel_name: str
    address: str
    location: dict[str, float]  # {"lat": ..., "lng": ...}
    next_flight_number: str
    next_flight_departure: datetime
    stars: int = 3
    price_per_night: int | None = None
    maps_uri: str = ""
    rating: str = ""


class GroundTransportDetails(CamelModel):
    mode: GroundMode
    route: str
    departure: datetime
    arrival: datetime
    provider: str


class AltAirportDetails(CamelModel):
    via_airport: str
    connecting_flight: str
    transfer_mode: TransferMode
    total_arrival: datetime


class LoungeDetails(CamelModel):
    lounge_name: str
    terminal: str
    location: str  # e.g. "Gate area B, Level 2"
    access_type: str  # "first_class", "senator", "business"
    amenities: list[str] = Field(default_factory=list)
    opening_hours: str = ""
    shower_available: bool = False
    sleeping_rooms: bool = False


class VoucherDetails(CamelModel):
    voucher_type: str  # "meal", "refreshment"
    amount_eur: int
    valid_until: datetime
    accepted_at: list[str] = Field(default_factory=list)  # Restaurant/shop names


type OptionDetails = RebookDetails | HotelDetails | GroundTransportDetails | AltAirportDetails | LoungeDetails | VoucherDetails


class Option(CamelModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    type: OptionType
    summary: str
    description: str
    details: OptionDetails
    available: bool = True
    estimated_arrival: datetime


class Wish(CamelModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    passenger_id: str
    disruption_id: str
    selected_option_id: str
    ranked_option_ids: list[str] = Field(default_factory=list)
    submitted_at: datetime
    status: WishStatus = WishStatus.PENDING
    denial_reason: str | None = None
    confirmation_details: str | None = None


# --- Request/Response helpers ---

class WishRequest(CamelModel):
    disruption_id: str
    selected_option_id: str
    ranked_option_ids: list[str] = Field(default_factory=list)


class DenyRequest(CamelModel):
    reason: str


class SimulateRequest(CamelModel):
    scenario: str = "munich_snowstorm"


class IngestEventRequest(CamelModel):
    """Raw disruption event — simulates what MQTT would deliver."""
    flight_number: str
    origin: str
    destination: str
    reason: str
    status_code: str = ""  # e.g. "CNL", "DVT", "DLY", "GCH"
    explanation: str = ""
