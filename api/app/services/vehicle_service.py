import uuid
from collections.abc import Sequence

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import User, Vehicle
from app.repositories.fuel_repository import FuelRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate

VEHICLE_NOT_FOUND = "Veículo não encontrado"
VEHICLE_HAS_SHIFTS = "Veículo possui expedientes registrados"
FUEL_NOT_FOUND = "Combustível não encontrado"


class VehicleService:
    def __init__(
        self, vehicle_repository: VehicleRepository, fuel_repository: FuelRepository
    ) -> None:
        self.vehicle_repository = vehicle_repository
        self.fuel_repository = fuel_repository

    def list(self, user: User) -> Sequence[Vehicle]:
        return self.vehicle_repository.list_by_user(user.id)

    def get(self, user: User, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.vehicle_repository.get_for_user(vehicle_id, user.id)
        if vehicle is None:
            raise NotFoundError(VEHICLE_NOT_FOUND)
        return vehicle

    def create(self, user: User, data: VehicleCreate) -> Vehicle:
        self._ensure_fuel_exists(data.fuel_id)
        return self.vehicle_repository.save(Vehicle(user_id=user.id, **data.model_dump()))

    def update(self, user: User, vehicle_id: uuid.UUID, data: VehicleUpdate) -> Vehicle:
        vehicle = self.get(user, vehicle_id)
        changes = data.model_dump(exclude_unset=True)
        if "fuel_id" in changes:
            self._ensure_fuel_exists(changes["fuel_id"])
        for field, value in changes.items():
            setattr(vehicle, field, value)
        return self.vehicle_repository.save(vehicle)

    def delete(self, user: User, vehicle_id: uuid.UUID) -> None:
        vehicle = self.get(user, vehicle_id)
        if self.vehicle_repository.has_shifts(vehicle.id):
            raise ConflictError(VEHICLE_HAS_SHIFTS)
        self.vehicle_repository.delete(vehicle)

    def _ensure_fuel_exists(self, fuel_id: uuid.UUID) -> None:
        if not self.fuel_repository.get_by_ids([fuel_id]):
            raise UnprocessableError(FUEL_NOT_FOUND)
