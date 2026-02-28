"""Port: Real-time notifications to passengers and dashboard clients.

Adapters:
  - WebSocketNotificationAdapter: pushes via the FastAPI WebSocket manager
  - (future) FCM/APNs adapter for mobile push notifications

Graceful degradation:
  Sending is fire-and-forget.  If the recipient has no active connection
  the message is silently dropped.  Adapters must never raise on send
  failures — log and continue.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NotificationPort(ABC):
    """Contract for pushing real-time events to connected clients."""

    @abstractmethod
    async def send_to_passenger(
        self,
        passenger_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send an event to a specific passenger's connected clients.

        Args:
            passenger_id: Unique passenger identifier.
            event_type: Event name (e.g. "disruption_notification",
                        "options_ready", "wish_approved").
            data: Arbitrary payload serialisable to JSON.

        The message is wrapped in the standard envelope format:
        ``{"type": event_type, "timestamp": ..., "data": data}``
        """

    @abstractmethod
    async def send_to_dashboard(
        self,
        disruption_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send an event to dashboard clients watching a disruption.

        Args:
            disruption_id: Disruption being monitored.
            event_type: Event name (e.g. "disruption_created",
                        "wish_submitted", "wish_approved").
            data: Arbitrary payload serialisable to JSON.
        """
