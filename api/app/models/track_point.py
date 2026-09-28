import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.shift import Shift


class TrackPoint(UUIDPrimaryKey, Base):
    __tablename__ = "track_points"
    __table_args__ = (
        UniqueConstraint("shift_id", "recorded_at", name="uq_track_points_shift_recorded_at"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
    )

    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    recorded_at: Mapped[datetime]
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    speed_ms: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    shift: Mapped["Shift"] = relationship(back_populates="track_points")
