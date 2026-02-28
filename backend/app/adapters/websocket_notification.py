"""Adapter: ConnectionManager -> NotificationPort.

Delegates WebSocket notification calls to the existing ConnectionManager
and catches all exceptions to ensure fire-and-forget semantics.
"""

from __future__ import annotations

import logging
from typing import Any

from app.ports.notification import NotificationPort
from app.ws import ConnectionManager

log = logging.getLogger(__name__)


class WebSocketNotificationAdapter(NotificationPort):
    """Sends real-time events via FastAPI WebSocket connections."""

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    async def send_to_passenger(
        self,
        passenger_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        try:
            await self._manager.send_to_passenger(passenger_id, event_type, data)
        except Exception:
            log.error(
                "WS send failed (passenger %s, event %s)", passenger_id, event_type, exc_info=True
            )

    async def send_to_dashboard(
        self,
        disruption_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        try:
            await self._manager.send_to_dashboard(disruption_id, event_type, data)
        except Exception:
            log.error(
                "WS send failed (dashboard %s, event %s)", disruption_id, event_type, exc_info=True
            )
