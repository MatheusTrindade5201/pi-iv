import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAt, UUIDPrimaryKey
from app.models.fuel import Fuel


class Vehicle(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("declared_kml > 0", name="declared_kml_positive"),
        CheckConstraint("displacement_cc > 0", name="displacement_cc_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    fuel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fuel.id"))
    model: Mapped[str] = mapped_column(String(120))
    declared_kml: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    displacement_cc: Mapped[int | None]
    year: Mapped[int | None]

    fuel: Mapped[Fuel] = relationship()
