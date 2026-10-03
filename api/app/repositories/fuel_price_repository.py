import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, selectinload

from app.models import FuelPrice


class FuelPriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def current_prices(self, user_id: uuid.UUID, at: datetime) -> Sequence[FuelPrice]:
        stmt = (
            select(FuelPrice)
            .options(selectinload(FuelPrice.fuel))
            .where(FuelPrice.user_id == user_id, FuelPrice.valid_from <= at)
            .ext(distinct_on(FuelPrice.fuel_id))
            .order_by(FuelPrice.fuel_id, FuelPrice.valid_from.desc())
        )
        return self.session.scalars(stmt).all()

    def current_price(
        self, user_id: uuid.UUID, fuel_id: uuid.UUID, at: datetime
    ) -> FuelPrice | None:
        stmt = (
            select(FuelPrice)
            .where(
                FuelPrice.user_id == user_id,
                FuelPrice.fuel_id == fuel_id,
                FuelPrice.valid_from <= at,
            )
            .order_by(FuelPrice.valid_from.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def add_all(self, prices: Iterable[FuelPrice]) -> None:
        self.session.add_all(prices)
        self.session.commit()
