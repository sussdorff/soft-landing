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


type OptionDetails = RebookDetails | HotelDetails | GroundTransportDetails | AltAirportDetails


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
