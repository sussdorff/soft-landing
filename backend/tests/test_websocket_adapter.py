"""Tests for WebSocketNotificationAdapter — verifies delegation and error handling."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.websocket_notification import WebSocketNotificationAdapter


@pytest.fixture
def mock_manager() -> AsyncMock:
    manager = AsyncMock()
    return manager


@pytest.fixture
def adapter(mock_manager: AsyncMock) -> WebSocketNotificationAdapter:
    return WebSocketNotificationAdapter(mock_manager)


# --- Delegation tests ---


async def test_send_to_passenger_delegates(adapter: WebSocketNotificationAdapter, mock_manager: AsyncMock):
    await adapter.send_to_passenger("pax-1", "options_ready", {"options": []})
    mock_manager.send_to_passenger.assert_awaited_once_with(
        "pax-1", "options_ready", {"options": []}
    )


async def test_send_to_dashboard_delegates(adapter: WebSocketNotificationAdapter, mock_manager: AsyncMock):
    await adapter.send_to_dashboard("dis-1", "wish_submitted", {"wish_id": "w1"})
    mock_manager.send_to_dashboard.assert_awaited_once_with(
        "dis-1", "wish_submitted", {"wish_id": "w1"}
    )


# --- Error handling tests ---


async def test_send_to_passenger_swallows_error(adapter: WebSocketNotificationAdapter, mock_manager: AsyncMock):
    mock_manager.send_to_passenger.side_effect = RuntimeError("connection reset")
    # Should not raise
    await adapter.send_to_passenger("pax-1", "options_ready", {})


async def test_send_to_dashboard_swallows_error(adapter: WebSocketNotificationAdapter, mock_manager: AsyncMock):
    mock_manager.send_to_dashboard.side_effect = ConnectionError("broken pipe")
    # Should not raise
    await adapter.send_to_dashboard("dis-1", "disruption_created", {})
