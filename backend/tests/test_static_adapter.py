"""Tests for StaticDataAdapter — verifies all port methods return proper types."""

import pytest

from app.adapters.static_data import StaticDataAdapter
from app.services.gemini import FlightContext, HotelOption, TransportOption


@pytest.fixture
def adapter() -> StaticDataAdapter:
    return StaticDataAdapter()


# --- GroundingPort methods ---


class TestFindNearbyHotels:
    async def test_returns_list_of_hotel_options(self, adapter: StaticDataAdapter):
        results = await adapter.find_nearby_hotels("MUC")
        assert isinstance(results, list)
        assert len(results) > 0
        for hotel in results:
            assert isinstance(hotel, HotelOption)

    async def test_respects_max_results(self, adapter: StaticDataAdapter):
        results = await adapter.find_nearby_hotels("MUC", max_results=2)
        assert len(results) <= 2

    async def test_unknown_airport_returns_hotels(self, adapter: StaticDataAdapter):
        # Static adapter always returns from the global pool regardless of airport
        results = await adapter.find_nearby_hotels("XYZ")
        assert isinstance(results, list)
        assert len(results) > 0

    async def test_hotel_fields_populated(self, adapter: StaticDataAdapter):
        results = await adapter.find_nearby_hotels("MUC", max_results=1)
        hotel = results[0]
        assert hotel.name
        assert hotel.address
        assert hotel.price_range
        assert hotel.rating


class TestFindGroundTransport:
    async def test_known_destination_returns_options(self, adapter: StaticDataAdapter):
        results = await adapter.find_ground_transport("MUC", "FRA")
        assert isinstance(results, list)
        assert len(results) > 0
        for opt in results:
            assert isinstance(opt, TransportOption)

    async def test_unknown_destination_returns_empty(self, adapter: StaticDataAdapter):
        results = await adapter.find_ground_transport("MUC", "XYZ")
        assert results == []

    async def test_transport_fields_populated(self, adapter: StaticDataAdapter):
        results = await adapter.find_ground_transport("MUC", "FRA")
        opt = results[0]
        assert opt.mode
        assert opt.provider
        assert opt.route
        assert opt.duration


class TestExplainDisruption:
    async def test_cancellation_template(self, adapter: StaticDataAdapter):
        text = await adapter.explain_disruption(
            "cancellation", "LH456", "MUC", "FRA", "Heavy snow",
        )
        assert "LH456" in text
        assert "cancelled" in text.lower()

    async def test_delay_template(self, adapter: StaticDataAdapter):
        text = await adapter.explain_disruption(
            "delay", "LH100", "MUC", "FRA", "Crew shortage",
        )
        assert "delay" in text.lower()

    async def test_unknown_type_uses_generic_template(self, adapter: StaticDataAdapter):
        text = await adapter.explain_disruption(
            "unknown_type", "LH999", "MUC", "CDG", "Reason",
        )
        assert "disrupted" in text.lower()
        assert "LH999" in text


class TestGetFlightContext:
    async def test_returns_empty_flight_context(self, adapter: StaticDataAdapter):
        ctx = await adapter.get_flight_context("LH456", "2026-03-01")
        assert isinstance(ctx, FlightContext)


class TestDescribeOption:
    async def test_returns_empty_string(self, adapter: StaticDataAdapter):
        result = await adapter.describe_option("rebook", {"flight": "LH100"})
        assert result == ""


# --- FlightDataPort methods ---


class TestGetSchedules:
    async def test_known_route_returns_schedule(self, adapter: StaticDataAdapter):
        data = await adapter.get_schedules("MUC", "FRA", "2026-03-01")
        assert "ScheduleResource" in data
        schedules = data["ScheduleResource"]["Schedule"]
        assert len(schedules) > 0

    async def test_unknown_route_returns_empty(self, adapter: StaticDataAdapter):
        data = await adapter.get_schedules("MUC", "XYZ", "2026-03-01")
        assert data == {}

    async def test_schedule_structure(self, adapter: StaticDataAdapter):
        data = await adapter.get_schedules("MUC", "FRA", "2026-03-01")
        sched = data["ScheduleResource"]["Schedule"][0]
        flight = sched["Flight"]
        assert "MarketingCarrier" in flight
        assert "Departure" in flight
        assert "Arrival" in flight


class TestGetLounges:
    async def test_known_airport_returns_lounges(self, adapter: StaticDataAdapter):
        data = await adapter.get_lounges("MUC")
        assert "LoungeResource" in data
        lounges = data["LoungeResource"]["Lounges"]["Lounge"]
        assert len(lounges) > 0

    async def test_unknown_airport_returns_empty(self, adapter: StaticDataAdapter):
        data = await adapter.get_lounges("XYZ")
        assert data == {}

    async def test_filtered_by_tier(self, adapter: StaticDataAdapter):
        data = await adapter.get_lounges("MUC", tier_code="HON")
        assert "LoungeResource" in data


class TestGetFlightStatus:
    async def test_returns_empty_dict(self, adapter: StaticDataAdapter):
        data = await adapter.get_flight_status("LH456", "2026-03-01")
        assert data == {}


class TestGetSeatMap:
    async def test_returns_empty_dict(self, adapter: StaticDataAdapter):
        data = await adapter.get_seat_map("LH456", "MUC", "FRA", "2026-03-01", "M")
        assert data == {}


class TestGetAirportInfo:
    async def test_returns_empty_dict(self, adapter: StaticDataAdapter):
        data = await adapter.get_airport_info("MUC")
        assert data == {}
