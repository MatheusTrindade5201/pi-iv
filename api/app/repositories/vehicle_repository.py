import uuid
from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.models import Shift, Vehicle


class VehicleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_user(self, user_id: uuid.UUID) -> Sequence[Vehicle]:
        stmt = (
            select(Vehicle)
            .options(selectinload(Vehicle.fuel))
            .where(Vehicle.user_id == user_id)
            .order_by(Vehicle.created_at, Vehicle.id)
        )
        return self.session.scalars(stmt).all()

    def get_for_user(self, vehicle_id: uuid.UUID, user_id: uuid.UUID) -> Vehicle | None:
        stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.user_id == user_id)
        return self.session.scalar(stmt)

    def has_shifts(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self.session.scalar(select(exists().where(Shift.vehicle_id == vehicle_id))))

    def save(self, vehicle: Vehicle) -> Vehicle:
        self.session.add(vehicle)
        self.session.commit()
        self.session.refresh(vehicle)
        return vehicle

    def delete(self, vehicle: Vehicle) -> None:
        self.session.delete(vehicle)
        self.session.commit()
