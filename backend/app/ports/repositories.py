"""Ports: persistent storage repositories.

Four repository contracts that abstract database access from business logic.

Adapters:
  - SQLAlchemy-backed implementations (refactored from store.py)

Graceful degradation:
  Repository methods raise on infrastructure errors (connection lost,
  constraint violation).  Business-logic callers are responsible for
  handling or propagating these.  ``get_*`` methods return None when
  the entity does not exist — callers must check.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.models import (
    Disruption,
    DisruptionType,
    Option,
    OptionDetails,
    Passenger,
    PassengerStatus,
    Wish,
)


# ---------------------------------------------------------------------------
# Disruption Repository
# ---------------------------------------------------------------------------


class DisruptionRepository(ABC):
    """Contract for disruption persistence."""

    @abstractmethod
    async def get_disruption(self, disruption_id: str) -> Disruption | None:
        """Fetch a single disruption by ID.

        Returns:
            The disruption, or None if not found.
        """

    @abstractmethod
    async def create_disruption(
        self,
        *,
        disruption_type: DisruptionType,
        flight_number: str,
        origin: str,
        destination: str,
        reason: str,
        explanation: str,
        affected_passenger_ids: list[str],
    ) -> str:
        """Create a disruption record and link affected passengers.

        Args:
            disruption_type: Classification of the event.
            flight_number: IATA flight number affected.
            origin: Origin airport IATA code.
            destination: Destination airport IATA code.
            reason: Technical reason from operations.
            explanation: Passenger-facing explanation text.
            affected_passenger_ids: Passenger IDs to link.

        Returns:
            The generated disruption ID.
        """

    @abstractmethod
    async def find_affected_passengers(
        self, flight_number: str,
    ) -> list[Passenger]:
        """Find passengers with a segment on the given flight.

        Results are sorted by priority descending, then by name.

        Args:
            flight_number: IATA flight number.

        Returns:
            List of affected passengers (may be empty).
        """

    @abstractmethod
    async def get_disruption_passengers(
        self, disruption_id: str,
    ) -> list[Passenger]:
        """Fetch all passengers linked to a disruption.

        Results are sorted by priority descending, then by name.

        Args:
            disruption_id: Unique disruption identifier.

        Returns:
            List of linked passengers (may be empty).
        """

    @abstractmethod
    async def is_empty(self) -> bool:
        """Check whether any disruptions exist in the store.

        Used for bootstrap seeding on first startup.

        Returns:
            True if no disruptions exist.
        """


# ---------------------------------------------------------------------------
# Passenger Repository
# ---------------------------------------------------------------------------


class PassengerRepository(ABC):
    """Contract for passenger persistence."""

    @abstractmethod
    async def get_passenger(self, passenger_id: str) -> Passenger | None:
        """Fetch a single passenger by ID.

        Returns:
            The passenger, or None if not found.
        """

    @abstractmethod
    async def get_passenger_disruptions(
        self, passenger_id: str,
    ) -> list[Disruption]:
        """Fetch all disruptions affecting a passenger.

        Args:
            passenger_id: Unique passenger identifier.

        Returns:
            List of disruptions (may be empty).
        """

    @abstractmethod
    async def update_passenger_status(
        self,
        passenger_id: str,
        status: PassengerStatus,
    ) -> None:
        """Update the passenger's workflow status.

        Args:
            passenger_id: Unique passenger identifier.
            status: New status value.

        Raises:
            ValueError: If the passenger does not exist.
        """


# ---------------------------------------------------------------------------
# Option Repository
# ---------------------------------------------------------------------------


class OptionRepository(ABC):
    """Contract for recovery-option persistence."""

    @abstractmethod
    async def create_option(
        self,
        *,
        passenger_id: str,
        option_type: str,
        summary: str,
        description: str,
        details: OptionDetails,
        available: bool,
        estimated_arrival: datetime,
    ) -> str:
        """Store a new recovery option for a passenger.

        Args:
            passenger_id: The passenger this option is for.
            option_type: OptionType value string.
            summary: Short one-line summary.
            description: Longer passenger-friendly description.
            details: Typed detail object (RebookDetails, HotelDetails, etc.).
            available: Whether the option can currently be selected.
            estimated_arrival: When the passenger would arrive at destination.

        Returns:
            The generated option ID.
        """

    @abstractmethod
    async def get_passenger_options(
        self, passenger_id: str,
    ) -> list[Option]:
        """Fetch all options for a passenger.

        Args:
            passenger_id: Unique passenger identifier.

        Returns:
            List of options (may be empty).
        """

    @abstractmethod
    async def delete_options(self, option_ids: list[str]) -> None:
        """Remove options by their IDs.

        Used to clean up stale options when a disruption is superseded.

        Args:
            option_ids: IDs of options to delete.  Missing IDs are ignored.
        """


# ---------------------------------------------------------------------------
# Wish Repository
# ---------------------------------------------------------------------------


class WishRepository(ABC):
    """Contract for passenger wish (preference selection) persistence."""

    @abstractmethod
    async def create_wish(
        self,
        *,
        passenger_id: str,
        disruption_id: str,
        selected_option_id: str,
        ranked_option_ids: list[str],
    ) -> Wish:
        """Record a passenger's option preference.

        Also updates the passenger's status to CHOSE.

        Args:
            passenger_id: Who submitted the wish.
            disruption_id: Which disruption this wish responds to.
            selected_option_id: The passenger's top choice.
            ranked_option_ids: All options in preference order.

        Returns:
            The created wish.
        """

    @abstractmethod
    async def approve_wish(self, wish_id: str) -> Wish | None:
        """Mark a wish as approved by the gate agent.

        Also updates the passenger's status to APPROVED.

        Args:
            wish_id: Unique wish identifier.

        Returns:
            The updated wish, or None if not found.
        """

    @abstractmethod
    async def deny_wish(
        self,
        wish_id: str,
        denial_reason: str,
    ) -> Wish | None:
        """Mark a wish as denied with a reason.

        Also updates the passenger's status to DENIED and
        increments their denial_count.

        Args:
            wish_id: Unique wish identifier.
            denial_reason: Human-readable reason for denial.

        Returns:
            The updated wish, or None if not found.
        """

    @abstractmethod
    async def get_wish(self, wish_id: str) -> Wish | None:
        """Fetch a single wish by ID.

        Returns:
            The wish, or None if not found.
        """

    @abstractmethod
    async def list_wishes(
        self,
        disruption_id: str | None = None,
    ) -> list[Wish]:
        """List wishes, optionally filtered by disruption.

        Args:
            disruption_id: If provided, only return wishes for this disruption.

        Returns:
            List of wishes (may be empty).
        """
