"""Async CRUD store backed by SQLAlchemy."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
    Disruption,
    DisruptionType,
    GroundTransportDetails,
    HotelDetails,
    Option,
    OptionType,
    Passenger,
    PassengerStatus,
    RebookDetails,
    Segment,
    TransferMode,
    Wish,
    WishStatus,
)


# --- Converters: ORM row -> Pydantic model ---

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
    )


def _details_from_json(opt_type: str, data: dict):
    match opt_type:
        case "rebook":
            return RebookDetails(**data)
        case "hotel":
            return HotelDetails(**data)
        case "ground":
            return GroundTransportDetails(**data)
        case "alt_airport":
            return AltAirportDetails(**data)
        case _:
            return data


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


# --- Query functions ---

async def get_disruption(session: AsyncSession, disruption_id: str) -> Disruption | None:
    stmt = (
        select(DisruptionRow)
        .where(DisruptionRow.id == disruption_id)
        .options(selectinload(DisruptionRow.passengers))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _row_to_disruption(row) if row else None


async def get_disruption_passengers(
    session: AsyncSession, disruption_id: str,
) -> list[Passenger]:
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


async def get_passenger(session: AsyncSession, passenger_id: str) -> Passenger | None:
    stmt = (
        select(PassengerRow)
        .where(PassengerRow.id == passenger_id)
        .options(selectinload(PassengerRow.segments))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _row_to_passenger(row) if row else None


async def get_passenger_options(
    session: AsyncSession, passenger_id: str,
) -> list[Option]:
    stmt = select(OptionRow).where(OptionRow.passenger_id == passenger_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_option(r) for r in rows]


async def get_passenger_disruptions(
    session: AsyncSession, passenger_id: str,
) -> list[Disruption]:
    stmt = (
        select(DisruptionRow)
        .join(DisruptionPassengerRow)
        .where(DisruptionPassengerRow.passenger_id == passenger_id)
        .options(selectinload(DisruptionRow.passengers))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_disruption(r) for r in rows]


async def create_wish(
    session: AsyncSession,
    *,
    passenger_id: str,
    disruption_id: str,
    selected_option_id: str,
    ranked_option_ids: list[str],
) -> Wish:
    wish_id = uuid4().hex[:8]
    row = WishRow(
        id=wish_id,
        passenger_id=passenger_id,
        disruption_id=disruption_id,
        selected_option_id=selected_option_id,
        ranked_option_ids_json=ranked_option_ids,
        submitted_at=datetime.now(tz=UTC),
        status="pending",
    )
    session.add(row)

    # Update passenger status
    pax = await session.get(PassengerRow, passenger_id)
    if pax:
        pax.status = "chose"

    await session.commit()
    return _row_to_wish(row)


async def get_wish(session: AsyncSession, wish_id: str) -> Wish | None:
    row = await session.get(WishRow, wish_id)
    return _row_to_wish(row) if row else None


async def approve_wish(session: AsyncSession, wish_id: str) -> Wish | None:
    row = await session.get(WishRow, wish_id)
    if not row:
        return None
    row.status = "approved"
    row.confirmation_details = "Approved by gate agent"

    pax = await session.get(PassengerRow, row.passenger_id)
    if pax:
        pax.status = "approved"

    await session.commit()
    return _row_to_wish(row)


async def deny_wish(
    session: AsyncSession, wish_id: str, reason: str,
) -> Wish | None:
    row = await session.get(WishRow, wish_id)
    if not row:
        return None
    row.status = "denied"
    row.denial_reason = reason

    pax = await session.get(PassengerRow, row.passenger_id)
    if pax:
        pax.status = "denied"
        pax.denial_count += 1

    await session.commit()
    return _row_to_wish(row)


async def list_wishes(
    session: AsyncSession, disruption_id: str | None = None,
) -> list[Wish]:
    stmt = select(WishRow)
    if disruption_id:
        stmt = stmt.where(WishRow.disruption_id == disruption_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_wish(r) for r in rows]


async def is_empty(session: AsyncSession) -> bool:
    stmt = select(DisruptionRow.id).limit(1)
    result = (await session.execute(stmt)).scalar_one_or_none()
    return result is None
