import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fuel


class FuelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> Sequence[Fuel]:
        return self.session.scalars(select(Fuel).order_by(Fuel.id)).all()

    def get_by_ids(self, fuel_ids: Collection[uuid.UUID]) -> Sequence[Fuel]:
        return self.session.scalars(select(Fuel).where(Fuel.id.in_(fuel_ids))).all()
