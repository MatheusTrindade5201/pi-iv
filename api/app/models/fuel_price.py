import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey
from app.models.fuel import Fuel


class FuelPrice(UUIDPrimaryKey, Base):
    __tablename__ = "fuel_prices"
    __table_args__ = (
        CheckConstraint("price_per_liter > 0", name="price_per_liter_positive"),
        Index("ix_fuel_prices_user_fuel_valid_from", "user_id", "fuel_id", "valid_from"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    fuel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fuel.id"))
    price_per_liter: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    valid_from: Mapped[datetime]

    fuel: Mapped[Fuel] = relationship()
