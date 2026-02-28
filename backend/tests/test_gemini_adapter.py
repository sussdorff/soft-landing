"""Tests for GeminiGroundingAdapter — None service, mock service, error handling."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.gemini_grounding import GeminiGroundingAdapter
from app.services.gemini import FlightContext, HotelOption, TransportOption


@pytest.fixture
def none_adapter() -> GeminiGroundingAdapter:
    """Adapter with no Gemini service (missing API key scenario)."""
    return GeminiGroundingAdapter(service=None)


@pytest.fixture
def mock_service() -> AsyncMock:
    svc = AsyncMock()
    svc.find_nearby_hotels = AsyncMock(return_value=[
        HotelOption(
            name="Test Hotel", address="123 Main St",
            distance="1km", price_range="100 EUR",
            rating="4.5", maps_uri="https://maps.example.com",
        ),
    ])
    svc.find_ground_transport = AsyncMock(return_value=[
        TransportOption(
            mode="train", provider="DB", route="MUC-FRA",
            departure="10:00", arrival="13:00", duration="3h",
        ),
    ])
    svc.explain_disruption = AsyncMock(return_value="AI-generated explanation")
    svc.get_flight_context = AsyncMock(return_value=FlightContext(
        weather_origin="Sunny, 15C",
    ))
    svc.describe_option = AsyncMock(return_value="AI-generated option description")
    return svc


@pytest.fixture
def mock_adapter(mock_service: AsyncMock) -> GeminiGroundingAdapter:
    return GeminiGroundingAdapter(service=mock_service)


# --- None service: graceful degradation ---


class TestNoneService:
    async def test_find_nearby_hotels_returns_empty(self, none_adapter):
        result = await none_adapter.find_nearby_hotels("MUC")
        assert result == []

    async def test_find_ground_transport_returns_empty(self, none_adapter):
        result = await none_adapter.find_ground_transport("MUC", "FRA")
        assert result == []

    async def test_explain_disruption_returns_fallback(self, none_adapter):
        result = await none_adapter.explain_disruption(
            "cancellation", "LH456", "MUC", "FRA", "weather",
        )
        assert "disruption" in result.lower()
        assert len(result) > 10

    async def test_get_flight_context_returns_empty(self, none_adapter):
        result = await none_adapter.get_flight_context("LH456", "2026-03-01")
        assert isinstance(result, FlightContext)

    async def test_describe_option_returns_terse_fallback(self, none_adapter):
        result = await none_adapter.describe_option("rebook", {"flight": "LH100"})
        assert "rebook" in result.lower()


# --- Mock service: delegation ---


class TestMockService:
    async def test_find_nearby_hotels_delegates(self, mock_adapter, mock_service):
        result = await mock_adapter.find_nearby_hotels("MUC", max_results=3)
        mock_service.find_nearby_hotels.assert_awaited_once_with("MUC", 3)
        assert len(result) == 1
        assert result[0].name == "Test Hotel"

    async def test_find_ground_transport_delegates(self, mock_adapter, mock_service):
        result = await mock_adapter.find_ground_transport("MUC", "FRA")
        mock_service.find_ground_transport.assert_awaited_once_with("MUC", "FRA")
        assert len(result) == 1

    async def test_explain_disruption_delegates(self, mock_adapter, mock_service):
        result = await mock_adapter.explain_disruption(
            "cancellation", "LH456", "MUC", "FRA", "snow",
        )
        mock_service.explain_disruption.assert_awaited_once()
        assert result == "AI-generated explanation"

    async def test_get_flight_context_delegates(self, mock_adapter, mock_service):
        result = await mock_adapter.get_flight_context("LH456", "2026-03-01")
        mock_service.get_flight_context.assert_awaited_once_with("LH456", "2026-03-01")
        assert result.weather_origin == "Sunny, 15C"

    async def test_describe_option_delegates(self, mock_adapter, mock_service):
        result = await mock_adapter.describe_option("rebook", {"flight": "LH100"})
        mock_service.describe_option.assert_awaited_once()
        assert result == "AI-generated option description"


# --- Error handling: service raises ---


class TestErrorHandling:
    async def test_find_nearby_hotels_swallows_error(self, mock_adapter, mock_service):
        mock_service.find_nearby_hotels.side_effect = RuntimeError("API error")
        result = await mock_adapter.find_nearby_hotels("MUC")
        assert result == []

    async def test_find_ground_transport_swallows_error(self, mock_adapter, mock_service):
        mock_service.find_ground_transport.side_effect = TimeoutError()
        result = await mock_adapter.find_ground_transport("MUC", "FRA")
        assert result == []

    async def test_explain_disruption_swallows_error(self, mock_adapter, mock_service):
        mock_service.explain_disruption.side_effect = ValueError("bad")
        result = await mock_adapter.explain_disruption(
            "delay", "LH456", "MUC", "FRA", "weather",
        )
        assert "disruption" in result.lower()

    async def test_get_flight_context_swallows_error(self, mock_adapter, mock_service):
        mock_service.get_flight_context.side_effect = ConnectionError()
        result = await mock_adapter.get_flight_context("LH456", "2026-03-01")
        assert isinstance(result, FlightContext)

    async def test_describe_option_swallows_error(self, mock_adapter, mock_service):
        mock_service.describe_option.side_effect = RuntimeError("oops")
        result = await mock_adapter.describe_option("hotel", {"name": "Hilton"})
        assert "hotel" in result.lower()
