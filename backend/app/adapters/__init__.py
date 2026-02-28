"""Adapter implementations — concrete port bindings.

Import adapters from this package for convenience::

    from app.adapters import StaticDataAdapter, SqlDisruptionRepository
"""

from app.adapters.gemini_grounding import GeminiGroundingAdapter
from app.adapters.lufthansa_api import LufthansaAPIAdapter
from app.adapters.repositories import (
    SqlDisruptionRepository,
    SqlOptionRepository,
    SqlPassengerRepository,
    SqlWishRepository,
)
from app.adapters.static_data import StaticDataAdapter
from app.adapters.websocket_notification import WebSocketNotificationAdapter

__all__ = [
    "GeminiGroundingAdapter",
    "LufthansaAPIAdapter",
    "SqlDisruptionRepository",
    "SqlOptionRepository",
    "SqlPassengerRepository",
    "SqlWishRepository",
    "StaticDataAdapter",
    "WebSocketNotificationAdapter",
]
