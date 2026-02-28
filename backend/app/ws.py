"""WebSocket connection manager."""

import json
from datetime import UTC, datetime

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for passengers and dashboard clients."""

    def __init__(self) -> None:
        self.passenger_connections: dict[str, list[WebSocket]] = {}
        self.dashboard_connections: dict[str, list[WebSocket]] = {}

    async def connect_passenger(self, passenger_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.passenger_connections.setdefault(passenger_id, []).append(ws)

    async def connect_dashboard(self, disruption_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.dashboard_connections.setdefault(disruption_id, []).append(ws)

    def disconnect_passenger(self, passenger_id: str, ws: WebSocket) -> None:
        conns = self.passenger_connections.get(passenger_id, [])
        if ws in conns:
            conns.remove(ws)

    def disconnect_dashboard(self, disruption_id: str, ws: WebSocket) -> None:
        conns = self.dashboard_connections.get(disruption_id, [])
        if ws in conns:
            conns.remove(ws)

    async def send_to_passenger(self, passenger_id: str, event_type: str, data: dict) -> None:
        msg = _envelope(event_type, data)
        for ws in self.passenger_connections.get(passenger_id, []):
            await ws.send_text(msg)

    async def send_to_dashboard(self, disruption_id: str, event_type: str, data: dict) -> None:
        msg = _envelope(event_type, data)
        for ws in self.dashboard_connections.get(disruption_id, []):
            await ws.send_text(msg)


def _envelope(event_type: str, data: dict) -> str:
    return json.dumps({
        "type": event_type,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "data": data,
    }, default=str)


manager = ConnectionManager()
