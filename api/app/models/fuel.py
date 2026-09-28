import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey

GASOLINE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
ETHANOL_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
FLEX_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")

SEED_FUELS = {
    GASOLINE_ID: "Gasolina",
    ETHANOL_ID: "Etanol",
    FLEX_ID: "Flex",
}


class Fuel(UUIDPrimaryKey, Base):
    __tablename__ = "fuel"

    name: Mapped[str] = mapped_column(String(50), unique=True)
