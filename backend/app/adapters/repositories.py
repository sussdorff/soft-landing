"""Adapters: SQLAlchemy-backed repository implementations.

Each class wraps an ``async_sessionmaker`` and implements one of the
repository port interfaces defined in ``app.ports.repositories``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db.tables import (
    DisruptionPassengerRow,
    DisruptionRow,
    OptionRow,
    PassengerRow,
    SegmentRow,
    WishRow,
)
from app.models import (
    AltAirportDetails,
    BookingClass,
    Disruption,
    DisruptionType,
    GroundTransportDetails,
    HotelDetails,
    LoungeDetails,
    LoyaltyTier,
    Option,
    OptionDetails,
    OptionType,
    Passenger,
    PassengerStatus,
    RebookDetails,
    Segment,
    VoucherDetails,
    Wish,
    WishStatus,
    cabin_class_from_booking,
)
from app.ports.repositories import (
    DisruptionRepository,
    OptionRepository,
    PassengerRepository,
    WishRepository,
)


# ---------------------------------------------------------------------------
# Internal converters: ORM row -> Pydantic model
# ---------------------------------------------------------------------------

def _row_to_disruption(row: DisruptionRow) -> Disruption:
    return Disruption(
        id=row.id,
        type=DisruptionType(row.type),
        flight_number=row.flight_number,
        origin=row.origin,
        destination=row.destination,
        reason=row.reason,
        explanation=row.explanation,
        detected_at=row.detected_at,
        affected_passenger_ids=[dp.passenger_id for dp in row.passengers],
    )


def _row_to_passenger(row: PassengerRow) -> Passenger:
    booking_cls = BookingClass(row.booking_class) if row.booking_class else BookingClass.Y
    loyalty = LoyaltyTier(row.loyalty_tier) if row.loyalty_tier else LoyaltyTier.NONE
    return Passenger(
        id=row.id,
        name=row.name,
        booking_ref=row.booking_ref,
        original_itinerary=[
            Segment(
                flight_number=s.flight_number,
                origin=s.origin,
                destination=s.destination,
                departure=s.departure,
                arrival=s.arrival,
            )
            for s in sorted(row.segments, key=lambda s: s.position)
        ],
        status=PassengerStatus(row.status),
        denial_count=row.denial_count,
        priority=row.priority,
        loyalty_tier=loyalty,
        booking_class=booking_cls,
        cabin_class=cabin_class_from_booking(booking_cls),
    )


def _details_from_json(opt_type: str, data: dict) -> OptionDetails:
    match opt_type:
        case "rebook":
            return RebookDetails(**data)
        case "hotel":
            return HotelDetails(**data)
        case "ground":
            return GroundTransportDetails(**data)
        case "alt_airport":
            return AltAirportDetails(**data)
        case "lounge":
            return LoungeDetails(**data)
        case "voucher":
            return VoucherDetails(**data)
        case _:
            return RebookDetails(**data)  # safe fallback


def _row_to_option(row: OptionRow) -> Option:
    return Option(
        id=row.id,
        type=OptionType(row.type),
        summary=row.summary,
        description=row.description,
        details=_details_from_json(row.type, row.details_json),
        available=row.available,
        estimated_arrival=row.estimated_arrival,
    )


def _row_to_wish(row: WishRow) -> Wish:
    return Wish(
        id=row.id,
        passenger_id=row.passenger_id,
        disruption_id=row.disruption_id,
        selected_option_id=row.selected_option_id,
        ranked_option_ids=row.ranked_option_ids_json or [],
        submitted_at=row.submitted_at,
        status=WishStatus(row.status),
        denial_reason=row.denial_reason,
        confirmation_details=row.confirmation_details,
    )


# ---------------------------------------------------------------------------
# SQLAlchemy Disruption Repository
# ---------------------------------------------------------------------------


class SqlDisruptionRepository(DisruptionRepository):
    """SQLAlchemy-backed disruption storage."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_disruption(self, disruption_id: str) -> Disruption | None:
        async with self._session_factory() as session:
            stmt = (
                select(DisruptionRow)
                .where(DisruptionRow.id == disruption_id)
                .options(selectinload(DisruptionRow.passengers))
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _row_to_disruption(row) if row else None

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
        disruption_id = uuid4().hex[:8]
        async with self._session_factory() as session:
            row = DisruptionRow(
                id=disruption_id,
                type=disruption_type.value,
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                reason=reason,
                explanation=explanation,
                detected_at=datetime.now(tz=UTC),
            )
            session.add(row)

            for pax_id in affected_passenger_ids:
                session.add(DisruptionPassengerRow(
                    disruption_id=disruption_id,
                    passenger_id=pax_id,
                ))
                # Mark passenger as notified
                pax = await session.get(PassengerRow, pax_id)
                if pax:
                    pax.status = PassengerStatus.NOTIFIED.value

            await session.commit()
        return disruption_id

    async def find_affected_passengers(
        self, flight_number: str,
    ) -> list[Passenger]:
        async with self._session_factory() as session:
            stmt = (
                select(PassengerRow)
                .join(SegmentRow)
                .where(SegmentRow.flight_number == flight_number)
                .options(selectinload(PassengerRow.segments))
            )
            rows = (await session.execute(stmt)).scalars().unique().all()
            pax = [_row_to_passenger(r) for r in rows]
            pax.sort(key=lambda p: (-p.priority, p.name))
            return pax

    async def get_disruption_passengers(
        self, disruption_id: str,
    ) -> list[Passenger]:
        async with self._session_factory() as session:
            stmt = (
                select(PassengerRow)
                .join(DisruptionPassengerRow)
                .where(DisruptionPassengerRow.disruption_id == disruption_id)
                .options(selectinload(PassengerRow.segments))
            )
            rows = (await session.execute(stmt)).scalars().all()
            pax = [_row_to_passenger(r) for r in rows]
            pax.sort(key=lambda p: (-p.priority, p.name))
            return pax

    async def find_disruption_by_flight(
        self, flight_number: str,
    ) -> Disruption | None:
        async with self._session_factory() as session:
            stmt = (
                select(DisruptionRow)
                .where(DisruptionRow.flight_number == flight_number)
                .options(selectinload(DisruptionRow.passengers))
                .order_by(DisruptionRow.detected_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _row_to_disruption(row) if row else None

    async def list_disruptions(self) -> list[Disruption]:
        async with self._session_factory() as session:
            stmt = (
                select(DisruptionRow)
                .options(selectinload(DisruptionRow.passengers))
            )
            rows = (await session.execute(stmt)).scalars().unique().all()
            return [_row_to_disruption(r) for r in rows]

    async def is_empty(self) -> bool:
        async with self._session_factory() as session:
            stmt = select(DisruptionRow.id).limit(1)
            result = (await session.execute(stmt)).scalar_one_or_none()
            return result is None


# ---------------------------------------------------------------------------
# SQLAlchemy Passenger Repository
# ---------------------------------------------------------------------------


class SqlPassengerRepository(PassengerRepository):
    """SQLAlchemy-backed passenger storage."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_passenger(self, passenger_id: str) -> Passenger | None:
        async with self._session_factory() as session:
            stmt = (
                select(PassengerRow)
                .where(PassengerRow.id == passenger_id)
                .options(selectinload(PassengerRow.segments))
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _row_to_passenger(row) if row else None

    async def get_passenger_disruptions(
        self, passenger_id: str,
    ) -> list[Disruption]:
        async with self._session_factory() as session:
            stmt = (
                select(DisruptionRow)
                .join(DisruptionPassengerRow)
                .where(DisruptionPassengerRow.passenger_id == passenger_id)
                .options(selectinload(DisruptionRow.passengers))
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_disruption(r) for r in rows]

    async def update_passenger_status(
        self,
        passenger_id: str,
        status: PassengerStatus,
    ) -> None:
        async with self._session_factory() as session:
            pax = await session.get(PassengerRow, passenger_id)
            if not pax:
                msg = f"Passenger {passenger_id} not found"
                raise ValueError(msg)
            pax.status = status.value
            if status == PassengerStatus.DENIED:
                pax.denial_count += 1
            await session.commit()

    async def update_passenger_priority(
        self,
        passenger_id: str,
        priority: int,
    ) -> None:
        async with self._session_factory() as session:
            pax = await session.get(PassengerRow, passenger_id)
            if not pax:
                msg = f"Passenger {passenger_id} not found"
                raise ValueError(msg)
            pax.priority = priority
            await session.commit()


# ---------------------------------------------------------------------------
# SQLAlchemy Option Repository
# ---------------------------------------------------------------------------


class SqlOptionRepository(OptionRepository):
    """SQLAlchemy-backed recovery-option storage."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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
        option_id = uuid4().hex[:8]
        async with self._session_factory() as session:
            row = OptionRow(
                id=option_id,
                passenger_id=passenger_id,
                type=option_type,
                summary=summary,
                description=description,
                details_json=details.model_dump(mode="json"),
                available=available,
                estimated_arrival=estimated_arrival,
            )
            session.add(row)
            await session.commit()
        return option_id

    async def get_option(self, option_id: str) -> Option | None:
        async with self._session_factory() as session:
            row = await session.get(OptionRow, option_id)
            return _row_to_option(row) if row else None

    async def get_passenger_options(
        self, passenger_id: str,
    ) -> list[Option]:
        async with self._session_factory() as session:
            stmt = select(OptionRow).where(OptionRow.passenger_id == passenger_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_option(r) for r in rows]

    async def get_disruption_options(
        self, disruption_id: str,
    ) -> dict[str, list[Option]]:
        async with self._session_factory() as session:
            stmt = (
                select(OptionRow)
                .join(DisruptionPassengerRow, OptionRow.passenger_id == DisruptionPassengerRow.passenger_id)
                .where(DisruptionPassengerRow.disruption_id == disruption_id)
            )
            rows = (await session.execute(stmt)).scalars().all()
            result: dict[str, list[Option]] = {}
            for row in rows:
                result.setdefault(row.passenger_id, []).append(_row_to_option(row))
            return result

    async def delete_options(self, option_ids: list[str]) -> None:
        if not option_ids:
            return
        async with self._session_factory() as session:
            stmt = delete(OptionRow).where(OptionRow.id.in_(option_ids))
            await session.execute(stmt)
            await session.commit()

    async def mark_unavailable(self, option_id: str) -> None:
        async with self._session_factory() as session:
            row = await session.get(OptionRow, option_id)
            if row:
                row.available = False
                await session.commit()


# ---------------------------------------------------------------------------
# SQLAlchemy Wish Repository
# ---------------------------------------------------------------------------


class SqlWishRepository(WishRepository):
    """SQLAlchemy-backed wish storage."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_wish(
        self,
        *,
        passenger_id: str,
        disruption_id: str,
        selected_option_id: str,
        ranked_option_ids: list[str],
    ) -> Wish:
        wish_id = uuid4().hex[:8]
        async with self._session_factory() as session:
            row = WishRow(
                id=wish_id,
                passenger_id=passenger_id,
                disruption_id=disruption_id,
                selected_option_id=selected_option_id,
                ranked_option_ids_json=ranked_option_ids,
                submitted_at=datetime.now(tz=UTC),
                status=WishStatus.PENDING.value,
            )
            session.add(row)

            # Update passenger status to "chose"
            pax = await session.get(PassengerRow, passenger_id)
            if pax:
                pax.status = PassengerStatus.CHOSE.value

            await session.commit()
            return _row_to_wish(row)

    async def approve_wish(
        self,
        wish_id: str,
        confirmation_details: str | None = None,
    ) -> Wish | None:
        async with self._session_factory() as session:
            row = await session.get(WishRow, wish_id)
            if not row:
                return None
            row.status = WishStatus.APPROVED.value
            row.confirmation_details = confirmation_details or "Approved by gate agent"

            pax = await session.get(PassengerRow, row.passenger_id)
            if pax:
                pax.status = PassengerStatus.APPROVED.value

            await session.commit()
            return _row_to_wish(row)

    async def deny_wish(
        self,
        wish_id: str,
        denial_reason: str,
    ) -> Wish | None:
        async with self._session_factory() as session:
            row = await session.get(WishRow, wish_id)
            if not row:
                return None
            row.status = WishStatus.DENIED.value
            row.denial_reason = denial_reason

            pax = await session.get(PassengerRow, row.passenger_id)
            if pax:
                pax.status = PassengerStatus.DENIED.value
                pax.denial_count += 1

            await session.commit()
            return _row_to_wish(row)

    async def get_wish(self, wish_id: str) -> Wish | None:
        async with self._session_factory() as session:
            row = await session.get(WishRow, wish_id)
            return _row_to_wish(row) if row else None

    async def list_wishes(
        self,
        disruption_id: str | None = None,
    ) -> list[Wish]:
        async with self._session_factory() as session:
            stmt = select(WishRow)
            if disruption_id:
                stmt = stmt.where(WishRow.disruption_id == disruption_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_wish(r) for r in rows]

    async def has_pending_wish(
        self,
        passenger_id: str,
        disruption_id: str,
    ) -> bool:
        async with self._session_factory() as session:
            stmt = (
                select(WishRow.id)
                .where(
                    WishRow.passenger_id == passenger_id,
                    WishRow.disruption_id == disruption_id,
                    WishRow.status == WishStatus.PENDING.value,
                )
                .limit(1)
            )
            result = (await session.execute(stmt)).scalar_one_or_none()
            return result is not None

    async def find_competing_wishes(
        self,
        disruption_id: str,
        option_id: str,
        exclude_passenger_id: str,
    ) -> list[Wish]:
        async with self._session_factory() as session:
            stmt = (
                select(WishRow)
                .where(
                    WishRow.disruption_id == disruption_id,
                    WishRow.selected_option_id == option_id,
                    WishRow.passenger_id != exclude_passenger_id,
                    WishRow.status == WishStatus.PENDING.value,
                )
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_row_to_wish(r) for r in rows]
