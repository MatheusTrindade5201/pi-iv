import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.earning import Earning
    from app.models.track_point import TrackPoint


class ShiftStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Shift(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "shifts"
    __table_args__ = (
        Index("ix_shifts_user_started_at", "user_id", "started_at"),
        Index(
            "uq_shifts_user_in_progress",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    fuel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fuel.id"))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    status: Mapped[ShiftStatus] = mapped_column(
        Enum(ShiftStatus, name="shift_status", values_callable=lambda e: [m.value for m in e])
    )
    price_per_liter_used: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    kml_used: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    idle_minutes: Mapped[int | None]
    fuel_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    earnings_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    profit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    duration_minutes: Mapped[int | None]
    profit_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    profit_per_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    earnings: Mapped[list["Earning"]] = relationship(
        back_populates="shift", cascade="all, delete-orphan", passive_deletes=True
    )
    track_points: Mapped[list["TrackPoint"]] = relationship(
        back_populates="shift", cascade="all, delete-orphan", passive_deletes=True
    )
