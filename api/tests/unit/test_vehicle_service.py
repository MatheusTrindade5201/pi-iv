import uuid
from collections.abc import Collection
from decimal import Decimal

import pytest

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import ETHANOL_ID, GASOLINE_ID, Fuel, User, Vehicle
from app.models.fuel import SEED_FUELS
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.vehicle_service import VehicleService

pytestmark = pytest.mark.unit


class FakeFuelRepository:
    def get_by_ids(self, fuel_ids: Collection[uuid.UUID]) -> list[Fuel]:
        return [
            Fuel(id=fuel_id, name=SEED_FUELS[fuel_id])
            for fuel_id in fuel_ids
            if fuel_id in SEED_FUELS
        ]


class FakeVehicleRepository:
    def __init__(self) -> None:
        self.vehicles: dict[uuid.UUID, Vehicle] = {}
        self.vehicles_with_shifts: set[uuid.UUID] = set()

    def list_by_user(self, user_id: uuid.UUID) -> list[Vehicle]:
        return [vehicle for vehicle in self.vehicles.values() if vehicle.user_id == user_id]

    def get_for_user(self, vehicle_id: uuid.UUID, user_id: uuid.UUID) -> Vehicle | None:
        vehicle = self.vehicles.get(vehicle_id)
        return vehicle if vehicle is not None and vehicle.user_id == user_id else None

    def has_shifts(self, vehicle_id: uuid.UUID) -> bool:
        return vehicle_id in self.vehicles_with_shifts

    def save(self, vehicle: Vehicle) -> Vehicle:
        vehicle.id = vehicle.id or uuid.uuid4()
        self.vehicles[vehicle.id] = vehicle
        return vehicle

    def delete(self, vehicle: Vehicle) -> None:
        del self.vehicles[vehicle.id]


def make_user() -> User:
    return User(id=uuid.uuid4(), name="John", email="john@example.com", password_hash="x")


@pytest.fixture
def repository() -> FakeVehicleRepository:
    return FakeVehicleRepository()


@pytest.fixture
def service(repository: FakeVehicleRepository) -> VehicleService:
    return VehicleService(repository, FakeFuelRepository())


@pytest.fixture
def user() -> User:
    return make_user()


def new_vehicle(**overrides: object) -> VehicleCreate:
    data = {"model": "Honda CG 160", "fuel_id": GASOLINE_ID, "declared_kml": "32", "year": 2022}
    return VehicleCreate(**(data | overrides))


def test_create_vehicle(service: VehicleService, user: User) -> None:
    vehicle = service.create(user, new_vehicle())

    assert vehicle.user_id == user.id
    assert vehicle.model == "Honda CG 160"
    assert service.list(user) == [vehicle]


def test_create_with_unknown_fuel_is_rejected(service: VehicleService, user: User) -> None:
    with pytest.raises(UnprocessableError, match="Combustível não encontrado"):
        service.create(user, new_vehicle(fuel_id=uuid.uuid4()))


def test_vehicle_of_other_user_is_not_found(service: VehicleService, user: User) -> None:
    vehicle = service.create(make_user(), new_vehicle())

    with pytest.raises(NotFoundError, match="Veículo não encontrado"):
        service.get(user, vehicle.id)


def test_partial_update_keeps_other_fields(service: VehicleService, user: User) -> None:
    vehicle = service.create(user, new_vehicle())

    updated = service.update(user, vehicle.id, VehicleUpdate(declared_kml="30", fuel_id=ETHANOL_ID))

    assert updated.declared_kml == Decimal("30")
    assert updated.fuel_id == ETHANOL_ID
    assert updated.model == "Honda CG 160"
    assert updated.year == 2022


def test_update_can_clear_optional_field(service: VehicleService, user: User) -> None:
    vehicle = service.create(user, new_vehicle())

    assert service.update(user, vehicle.id, VehicleUpdate(year=None)).year is None


def test_update_with_unknown_fuel_is_rejected(service: VehicleService, user: User) -> None:
    vehicle = service.create(user, new_vehicle())

    with pytest.raises(UnprocessableError):
        service.update(user, vehicle.id, VehicleUpdate(fuel_id=uuid.uuid4()))


def test_delete_vehicle_with_shifts_is_rejected(
    service: VehicleService, repository: FakeVehicleRepository, user: User
) -> None:
    vehicle = service.create(user, new_vehicle())
    repository.vehicles_with_shifts.add(vehicle.id)

    with pytest.raises(ConflictError, match="Veículo possui expedientes registrados"):
        service.delete(user, vehicle.id)
    assert service.list(user) == [vehicle]


def test_delete_vehicle(service: VehicleService, user: User) -> None:
    vehicle = service.create(user, new_vehicle())

    service.delete(user, vehicle.id)

    assert service.list(user) == []
