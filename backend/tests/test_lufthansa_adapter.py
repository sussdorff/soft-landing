"""Tests for LufthansaAPIAdapter — verifies delegation and error handling."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.lufthansa_api import LufthansaAPIAdapter
from app.services.lufthansa import LufthansaAPIError


@pytest.fixture
def mock_client() -> AsyncMock:
    """A mock LufthansaClient with default return values."""
    client = AsyncMock()
    client.get_schedules.return_value = {"ScheduleResource": []}
    client.get_lounges.return_value = {"LoungeResource": []}
    client.get_flight_status.return_value = {"FlightStatusResource": {}}
    client.get_seat_map.return_value = {"SeatAvailabilityResource": {}}
    client.get_airport_info.return_value = {"AirportResource": {}}
    return client


@pytest.fixture
def adapter(mock_client: AsyncMock) -> LufthansaAPIAdapter:
    return LufthansaAPIAdapter(mock_client)


# --- Delegation tests ---


async def test_get_schedules_delegates(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    result = await adapter.get_schedules("MUC", "FRA", "2026-03-01", direct_flights=True)
    mock_client.get_schedules.assert_awaited_once_with(
        "MUC", "FRA", "2026-03-01", direct_flights=True
    )
    assert result == {"ScheduleResource": []}


async def test_get_lounges_delegates(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    result = await adapter.get_lounges("FRA", tier_code="SEN")
    mock_client.get_lounges.assert_awaited_once_with(
        "FRA", cabin_class=None, tier_code="SEN"
    )
    assert result == {"LoungeResource": []}


async def test_get_flight_status_delegates(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    result = await adapter.get_flight_status("LH400", "2026-03-01")
    mock_client.get_flight_status.assert_awaited_once_with("LH400", "2026-03-01")
    assert result == {"FlightStatusResource": {}}


async def test_get_seat_map_delegates(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    result = await adapter.get_seat_map("LH400", "MUC", "FRA", "2026-03-01", "M")
    mock_client.get_seat_map.assert_awaited_once_with(
        "LH400", "MUC", "FRA", "2026-03-01", "M"
    )
    assert result == {"SeatAvailabilityResource": {}}


async def test_get_airport_info_delegates(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    result = await adapter.get_airport_info("MUC")
    mock_client.get_airport_info.assert_awaited_once_with("MUC")
    assert result == {"AirportResource": {}}


# --- Error handling tests ---


async def test_get_schedules_returns_empty_on_error(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    mock_client.get_schedules.side_effect = LufthansaAPIError(500, "Server Error")
    result = await adapter.get_schedules("MUC", "FRA", "2026-03-01")
    assert result == {}


async def test_get_lounges_returns_empty_on_error(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    mock_client.get_lounges.side_effect = RuntimeError("connection lost")
    result = await adapter.get_lounges("FRA")
    assert result == {}


async def test_get_flight_status_returns_empty_on_error(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    mock_client.get_flight_status.side_effect = LufthansaAPIError(429, "Rate limited")
    result = await adapter.get_flight_status("LH400", "2026-03-01")
    assert result == {}


async def test_get_seat_map_returns_empty_on_error(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    mock_client.get_seat_map.side_effect = TimeoutError()
    result = await adapter.get_seat_map("LH400", "MUC", "FRA", "2026-03-01", "C")
    assert result == {}


async def test_get_airport_info_returns_empty_on_error(adapter: LufthansaAPIAdapter, mock_client: AsyncMock):
    mock_client.get_airport_info.side_effect = LufthansaAPIError(404, "Not found")
    result = await adapter.get_airport_info("XYZ")
    assert result == {}
