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
    WishRow,
)
from app.models import (
    AltAirportDetails,
    BookingClass,
    CabinClass,
    Disruption,
    DisruptionType,
    GroundTransportDetails,
    HotelDetails,
    LoungeDetails,
    LoyaltyTier,
    Option,
    OptionType,
    Passenger,
    PassengerStatus,
    RebookDetails,
    Segment,
    ServiceLevel,
    VoucherDetails,
    Wish,
    WishStatus,
    _FULL_FARE_ECONOMY,
    cabin_class_from_booking,
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
        case "lounge":
            return LoungeDetails(**data)
        case "voucher":
            return VoucherDetails(**data)
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


# --- Service level computation ---

def compute_service_level(
    loyalty_tier: LoyaltyTier, booking_class: BookingClass,
) -> ServiceLevel:
    """Compute service recovery parameters from passenger profile.

    Priority matrix based on Lufthansa disruption management research:
    - Loyalty tier contributes: HON +40, SEN +25, FTL +10, NONE +0
    - Cabin/fare contributes:  First +30, Business +20, PremEco +10,
                               Economy full-fare(Y/B) +5, Economy discounted +0
    """
    cabin = cabin_class_from_booking(booking_class)

    # --- Priority score ---
    tier_score = {
        LoyaltyTier.HON_CIRCLE: 40,
        LoyaltyTier.SENATOR: 25,
        LoyaltyTier.FREQUENT_TRAVELLER: 10,
        LoyaltyTier.NONE: 0,
    }[loyalty_tier]

    cabin_score: int
    if cabin == CabinClass.FIRST:
        cabin_score = 30
    elif cabin == CabinClass.BUSINESS:
        cabin_score = 20
    elif cabin == CabinClass.PREMIUM_ECONOMY:
        cabin_score = 10
    elif booking_class in _FULL_FARE_ECONOMY:
        cabin_score = 5
    else:
        cabin_score = 0

    priority_score = tier_score + cabin_score

    # --- Service parameters by combined tier ---
    # HON Circle (any cabin)
    if loyalty_tier == LoyaltyTier.HON_CIRCLE:
        return ServiceLevel(
            priority_score=priority_score,
            hotel_stars=5,
            hotel_budget_eur=200,
            transport_mode="limousine",
            lounge_access="first_class",
            meal_voucher_eur=0,  # Lounge access covers meals
            rebooking_scope="any_airline",
            upgrade_eligible=True,
        )

    # Senator or Business cabin
    if loyalty_tier == LoyaltyTier.SENATOR or cabin in (
        CabinClass.BUSINESS, CabinClass.FIRST,
    ):
        return ServiceLevel(
            priority_score=priority_score,
            hotel_stars=4,
            hotel_budget_eur=150,
            transport_mode="taxi",
            lounge_access="senator" if loyalty_tier == LoyaltyTier.SENATOR else "business",
            meal_voucher_eur=0,  # Lounge access covers meals
            rebooking_scope="star_alliance",
            upgrade_eligible=True,
        )

    # FTL or full-fare Economy
    if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER or booking_class in _FULL_FARE_ECONOMY:
        return ServiceLevel(
            priority_score=priority_score,
            hotel_stars=4 if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER else 3,
            hotel_budget_eur=100,
            transport_mode="shuttle",
            lounge_access="business" if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER else "none",
            meal_voucher_eur=0 if loyalty_tier == LoyaltyTier.FREQUENT_TRAVELLER else 15,
            rebooking_scope="lh_group",
            upgrade_eligible=False,
        )

    # Premium Economy (no special status)
    if cabin == CabinClass.PREMIUM_ECONOMY:
        return ServiceLevel(
            priority_score=priority_score,
            hotel_stars=3,
            hotel_budget_eur=100,
            transport_mode="shuttle",
            lounge_access="none",
            meal_voucher_eur=15,
            rebooking_scope="lh_group",
            upgrade_eligible=False,
        )

    # Economy discounted, no status — baseline
    return ServiceLevel(
        priority_score=priority_score,
        hotel_stars=3,
        hotel_budget_eur=80,
        transport_mode="shuttle",
        lounge_access="none",
        meal_voucher_eur=12,
        rebooking_scope="lh_group",
        upgrade_eligible=False,
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
