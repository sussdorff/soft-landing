"""Tests for OptionGenerator with mock ports."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.models import (
    BookingClass,
    DisruptionType,
    LoyaltyTier,
)
from app.ports.flight_data import FlightDataPort
from app.ports.grounding import GroundingPort
from app.ports.repositories import OptionRepository
from app.services.gemini import HotelOption, TransportOption
from app.services.option_generator import OptionGenerator


@pytest.fixture
def mock_flight_data() -> FlightDataPort:
    fd = AsyncMock(spec=FlightDataPort)
    fd.get_schedules.return_value = {
        "ScheduleResource": {
            "Schedule": [{
                "Flight": {
                    "MarketingCarrier": {"AirlineID": "LH", "FlightNumber": "98"},
                    "Departure": {
                        "AirportCode": "MUC",
                        "ScheduledTimeLocal": {"DateTime": "2026-03-02T06:30"},
                    },
                    "Arrival": {"AirportCode": "FRA"},
                },
            }],
        },
    }
    fd.get_lounges.return_value = {}
    fd.get_flight_status.return_value = {}
    fd.get_seat_map.return_value = {}
    fd.get_airport_info.return_value = {}
    return fd


@pytest.fixture
def mock_grounding() -> GroundingPort:
    g = AsyncMock(spec=GroundingPort)
    g.find_nearby_hotels.return_value = [
        HotelOption(
            name="Hilton Airport", address="Terminal St 20",
            distance="200m", price_range="200 EUR",
            rating="4.5", maps_uri="",
        ),
    ]
    g.find_ground_transport.return_value = [
        TransportOption(
            mode="train", provider="DB", route="ICE MUC-FRA",
            departure="10:00", arrival="13:00", duration="3h",
        ),
    ]
    g.explain_disruption.return_value = "Explanation"
    g.get_flight_context.return_value = None
    g.describe_option.return_value = ""
    return g


@pytest.fixture
def mock_option_repo() -> OptionRepository:
    repo = AsyncMock(spec=OptionRepository)
    # Return incrementing IDs
    repo.create_option.side_effect = [
        f"opt-{i:03d}" for i in range(1, 50)
    ]
    return repo


@pytest.fixture
def generator(mock_flight_data, mock_grounding, mock_option_repo) -> OptionGenerator:
    return OptionGenerator(mock_flight_data, mock_grounding, mock_option_repo)


class TestGenerateOptions:
    async def test_gate_change_returns_no_options(self, generator, mock_option_repo):
        ids = await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.GATE_CHANGE, "FRA",
        )
        assert ids == []
        mock_option_repo.create_option.assert_not_called()

    async def test_cancellation_generates_multiple_options(self, generator, mock_option_repo):
        ids = await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        # Should generate: rebook, hotel, ground, alt_airport, voucher (no lounge for none tier)
        assert len(ids) >= 3  # At minimum rebook + hotel + ground
        assert mock_option_repo.create_option.call_count >= 3

    async def test_delay_generates_options(self, generator, mock_option_repo):
        ids = await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.DELAY, "FRA",
        )
        # Delay should not generate alt_airport
        assert len(ids) >= 3  # rebook + hotel + ground at minimum

    async def test_creates_rebook_option(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        # First call should be rebook
        first_call = mock_option_repo.create_option.call_args_list[0]
        assert first_call.kwargs["option_type"] == "rebook"
        assert first_call.kwargs["passenger_id"] == "pax-001"

    async def test_creates_hotel_option(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "hotel" in types_created

    async def test_creates_ground_option(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "ground" in types_created

    async def test_cancellation_includes_alt_airport(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "alt_airport" in types_created

    async def test_delay_excludes_alt_airport(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.DELAY, "FRA",
        )
        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "alt_airport" not in types_created

    async def test_queries_flight_data_port(self, generator, mock_flight_data):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        mock_flight_data.get_schedules.assert_called_once()
        call_args = mock_flight_data.get_schedules.call_args
        assert call_args.args[0] == "MUC"
        assert call_args.args[1] == "FRA"

    async def test_queries_grounding_for_hotels(self, generator, mock_grounding):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        mock_grounding.find_nearby_hotels.assert_called_once_with("MUC")

    async def test_queries_grounding_for_transport(self, generator, mock_grounding):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
        )
        mock_grounding.find_ground_transport.assert_called()


class TestServiceLevelDifferentiation:
    async def test_senator_gets_lounge(self, generator, mock_flight_data, mock_option_repo):
        # Senator should get lounge access — provide lounge data
        mock_flight_data.get_lounges.return_value = {
            "LoungeResource": {
                "Lounges": {
                    "Lounge": [{
                        "Names": {"Name": [{"$": "Senator Lounge", "@LanguageCode": "en"}]},
                        "Locations": {"Location": [{"$": "Gate H", "@LanguageCode": "en"}]},
                        "OpeningHours": {"OpeningHour": [{"$": "06:00-22:00", "@LanguageCode": "en"}]},
                        "Features": {
                            "ShowerFacilities": "true",
                            "RelaxingRooms": "false",
                        },
                    }],
                },
            },
        }

        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
            loyalty_tier=LoyaltyTier.SENATOR,
            booking_class=BookingClass.C,
        )

        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "lounge" in types_created

    async def test_economy_gets_meal_voucher(self, generator, mock_option_repo):
        await generator.generate_options(
            "dis-001", "pax-001", DisruptionType.CANCELLATION, "FRA",
            loyalty_tier=LoyaltyTier.NONE,
            booking_class=BookingClass.Y,
        )

        types_created = [
            call.kwargs["option_type"]
            for call in mock_option_repo.create_option.call_args_list
        ]
        assert "voucher" in types_created


class TestParseScheduleCandidates:
    def test_parses_valid_schedule(self):
        data = {
            "ScheduleResource": {
                "Schedule": [{
                    "Flight": {
                        "MarketingCarrier": {"AirlineID": "LH", "FlightNumber": "98"},
                        "Departure": {
                            "AirportCode": "MUC",
                            "ScheduledTimeLocal": {"DateTime": "2026-03-01T06:30"},
                        },
                        "Arrival": {"AirportCode": "FRA"},
                    },
                }],
            },
        }
        candidates = OptionGenerator._parse_schedule_candidates(data, "MUC", "FRA")
        assert len(candidates) == 1
        assert candidates[0] == ("LH98", "MUC", "FRA", 6, 30)

    def test_empty_schedule(self):
        assert OptionGenerator._parse_schedule_candidates({}, "MUC", "FRA") == []

    def test_single_schedule_dict(self):
        data = {
            "ScheduleResource": {
                "Schedule": {
                    "Flight": {
                        "MarketingCarrier": {"AirlineID": "LH", "FlightNumber": "100"},
                        "Departure": {
                            "AirportCode": "MUC",
                            "ScheduledTimeLocal": {"DateTime": "2026-03-01T08:00"},
                        },
                        "Arrival": {"AirportCode": "FRA"},
                    },
                },
            },
        }
        candidates = OptionGenerator._parse_schedule_candidates(data, "MUC", "FRA")
        assert len(candidates) == 1
        assert candidates[0][0] == "LH100"


class TestParseBestLounge:
    def test_parses_lounge_data(self):
        data = {
            "LoungeResource": {
                "Lounges": {
                    "Lounge": [{
                        "Names": {"Name": [{"$": "Senator Lounge", "@LanguageCode": "en"}]},
                        "Locations": {"Location": [{"$": "Gate H", "@LanguageCode": "en"}]},
                        "OpeningHours": {"OpeningHour": [{"$": "06:00-22:00", "@LanguageCode": "en"}]},
                        "Features": {
                            "ShowerFacilities": "true",
                            "RelaxingRooms": "false",
                        },
                    }],
                },
            },
        }
        lounge = OptionGenerator._parse_best_lounge(data, "senator")
        assert lounge is not None
        assert lounge["name"] == "Senator Lounge"
        assert lounge["shower_available"] is True

    def test_empty_data_returns_none(self):
        assert OptionGenerator._parse_best_lounge({}, "senator") is None

    def test_no_lounges_returns_none(self):
        data = {"LoungeResource": {"Lounges": {"Lounge": []}}}
        assert OptionGenerator._parse_best_lounge(data, "senator") is None
