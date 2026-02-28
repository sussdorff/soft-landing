"""Port interfaces — contracts between business logic and infrastructure.

Import all ports from this package for convenience::

    from app.ports import FlightDataPort, GroundingPort, NotificationPort
    from app.ports import DisruptionRepository, PassengerRepository
    from app.ports import OptionRepository, WishRepository
"""

from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.ports.notification import NotificationPort
from app.ports.repositories import (
    DisruptionRepository,
    OptionRepository,
    PassengerRepository,
    WishRepository,
)

__all__ = [
    "DisruptionRepository",
    "FlightDataPort",
    "GroundingPort",
    "NotificationPort",
    "OptionRepository",
    "PassengerRepository",
    "WishRepository",
]
