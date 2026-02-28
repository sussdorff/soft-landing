"""SQLAlchemy ORM models for the ReRoute database."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DisruptionRow(Base):
    __tablename__ = "disruptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    flight_number: Mapped[str] = mapped_column(String(10))
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    passengers: Mapped[list["DisruptionPassengerRow"]] = relationship(
        back_populates="disruption", cascade="all, delete-orphan",
    )


class PassengerRow(Base):
    __tablename__ = "passengers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    booking_ref: Mapped[str] = mapped_column(String(6))
    status: Mapped[str] = mapped_column(String(20), default="unaffected")
    denial_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    segments: Mapped[list["SegmentRow"]] = relationship(
        back_populates="passenger", cascade="all, delete-orphan",
        order_by="SegmentRow.position",
    )
    disruptions: Mapped[list["DisruptionPassengerRow"]] = relationship(
        back_populates="passenger", cascade="all, delete-orphan",
    )
    options: Mapped[list["OptionRow"]] = relationship(
        back_populates="passenger", cascade="all, delete-orphan",
    )
    wishes: Mapped[list["WishRow"]] = relationship(
        back_populates="passenger", cascade="all, delete-orphan",
    )


class SegmentRow(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    passenger_id: Mapped[str] = mapped_column(ForeignKey("passengers.id"))
    flight_number: Mapped[str] = mapped_column(String(10))
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    departure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer)

    passenger: Mapped["PassengerRow"] = relationship(back_populates="segments")


class DisruptionPassengerRow(Base):
    __tablename__ = "disruption_passengers"

    disruption_id: Mapped[str] = mapped_column(
        ForeignKey("disruptions.id"), primary_key=True,
    )
    passenger_id: Mapped[str] = mapped_column(
        ForeignKey("passengers.id"), primary_key=True,
    )

    disruption: Mapped["DisruptionRow"] = relationship(back_populates="passengers")
    passenger: Mapped["PassengerRow"] = relationship(back_populates="disruptions")


class OptionRow(Base):
    __tablename__ = "options"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    passenger_id: Mapped[str] = mapped_column(ForeignKey("passengers.id"))
    type: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(JSON)
    available: Mapped[bool] = mapped_column(default=True)
    estimated_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    passenger: Mapped["PassengerRow"] = relationship(back_populates="options")


class WishRow(Base):
    __tablename__ = "wishes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    passenger_id: Mapped[str] = mapped_column(ForeignKey("passengers.id"))
    disruption_id: Mapped[str] = mapped_column(ForeignKey("disruptions.id"))
    selected_option_id: Mapped[str] = mapped_column(String(64))
    ranked_option_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    passenger: Mapped["PassengerRow"] = relationship(back_populates="wishes")
