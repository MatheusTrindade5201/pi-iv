import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.shift import Shift


class Earning(UUIDPrimaryKey, Base):
    __tablename__ = "earnings"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_earnings_shift_earned_at", "shift_id", "earned_at"),
    )

    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    platform: Mapped[str | None] = mapped_column(String(50))
    earned_at: Mapped[datetime]

    shift: Mapped["Shift"] = relationship(back_populates="earnings")
