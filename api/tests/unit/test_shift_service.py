import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    ETHANOL_ID,
    FLEX_ID,
    GASOLINE_ID,
    Earning,
    FuelPrice,
    Shift,
    ShiftStatus,
    TrackPoint,
    User,
    Vehicle,
)
from app.schemas.shift import ShiftStart
from app.services.calculations import CalculationParams
from app.services.shift_service import ShiftService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)


class FakeShiftRepository:
    def __init__(self) -> None:
        self.shifts: dict[uuid.UUID, Shift] = {}
        self.fail_on_save = False
        self.list_calls: list[tuple] = []

    def get_for_user(self, shift_id: uuid.UUID, user_id: uuid.UUID) -> Shift | None:
        shift = self.shifts.get(shift_id)
        return shift if shift is not None and shift.user_id == user_id else None

    def get_in_progress(self, user_id: uuid.UUID) -> Shift | None:
        return next(
            (
                shift
                for shift in self.shifts.values()
                if shift.user_id == user_id and shift.status == ShiftStatus.IN_PROGRESS
            ),
            None,
        )

    def list_for_user(self, user_id, start, end, offset, limit):
        self.list_calls.append((user_id, start, end, offset, limit))
        return [], 0

    def save(self, shift: Shift) -> Shift:
        if self.fail_on_save:
            raise IntegrityError("INSERT", {}, Exception("unique"))
        shift.id = shift.id or uuid.uuid4()
        self.shifts[shift.id] = shift
        return shift

    def rollback(self) -> None:
        pass


class FakeVehicleRepository:
    def __init__(self) -> None:
        self.vehicles: dict[uuid.UUID, Vehicle] = {}

    def get_for_user(self, vehicle_id: uuid.UUID, user_id: uuid.UUID) -> Vehicle | None:
        vehicle = self.vehicles.get(vehicle_id)
        return vehicle if vehicle is not None and vehicle.user_id == user_id else None


class FakeFuelPriceRepository:
    def __init__(self) -> None:
        self.prices: dict[uuid.UUID, Decimal] = {}

    def current_price(self, user_id: uuid.UUID, fuel_id: uuid.UUID, at: datetime):
        price = self.prices.get(fuel_id)
        if price is None:
            return None
        return FuelPrice(user_id=user_id, fuel_id=fuel_id, price_per_liter=price, valid_from=at)


class FakeEarningRepository:
    def __init__(self) -> None:
        self.earnings: list[Earning] = []

    def list_for_shift(self, shift_id: uuid.UUID) -> list[Earning]:
        return [earning for earning in self.earnings if earning.shift_id == shift_id]


class FakeTrackPointRepository:
    def __init__(self) -> None:
        self.points: list[TrackPoint] = []

    def list_for_shift(self, shift_id: uuid.UUID) -> list[TrackPoint]:
        return sorted(
            (point for point in self.points if point.shift_id == shift_id),
            key=lambda point: point.recorded_at,
        )


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def repos() -> dict:
    return {
        "shifts": FakeShiftRepository(),
        "vehicles": FakeVehicleRepository(),
        "prices": FakeFuelPriceRepository(),
        "earnings": FakeEarningRepository(),
        "track_points": FakeTrackPointRepository(),
    }


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def service(repos: dict, clock: Clock) -> ShiftService:
    return ShiftService(**repos, params=CalculationParams(), clock=clock)


@pytest.fixture
def user() -> User:
    return User(id=uuid.uuid4(), name="John", email="john@example.com", password_hash="x")


def add_vehicle(repos: dict, user: User, fuel_id: uuid.UUID = GASOLINE_ID) -> Vehicle:
    vehicle = Vehicle(
        id=uuid.uuid4(), user_id=user.id, fuel_id=fuel_id, model="Honda", declared_kml=Decimal("32")
    )
    repos["vehicles"].vehicles[vehicle.id] = vehicle
    return vehicle


def test_start_takes_snapshot_of_price_and_consumption(
    service: ShiftService, repos: dict, user: User
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.200")

    detail = service.start(user, ShiftStart(vehicle_id=vehicle.id))

    shift = detail.shift
    assert shift.status == ShiftStatus.IN_PROGRESS
    assert shift.started_at == NOW
    assert shift.fuel_id == GASOLINE_ID
    assert shift.price_per_liter_used == Decimal("6.200")
    assert shift.kml_used == Decimal("32")
    assert detail.summary.duration_minutes == 0


def test_start_with_vehicle_of_other_user_is_not_found(
    service: ShiftService, repos: dict, user: User
) -> None:
    other = User(id=uuid.uuid4())
    vehicle = add_vehicle(repos, other)

    with pytest.raises(NotFoundError, match="Veículo não encontrado"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id))


@pytest.mark.parametrize("fuel_id", [None, FLEX_ID, uuid.uuid4()])
def test_flex_vehicle_requires_gasoline_or_ethanol(
    service: ShiftService, repos: dict, user: User, fuel_id: uuid.UUID | None
) -> None:
    vehicle = add_vehicle(repos, user, FLEX_ID)

    with pytest.raises(UnprocessableError, match="Flex"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id, fuel_id=fuel_id))


def test_flex_vehicle_uses_chosen_fuel_price(
    service: ShiftService, repos: dict, user: User
) -> None:
    vehicle = add_vehicle(repos, user, FLEX_ID)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.200")
    repos["prices"].prices[ETHANOL_ID] = Decimal("3.750")

    shift = service.start(user, ShiftStart(vehicle_id=vehicle.id, fuel_id=ETHANOL_ID)).shift

    assert shift.fuel_id == ETHANOL_ID
    assert shift.price_per_liter_used == Decimal("3.750")


def test_non_flex_vehicle_rejects_other_fuel(
    service: ShiftService, repos: dict, user: User
) -> None:
    vehicle = add_vehicle(repos, user, GASOLINE_ID)

    with pytest.raises(UnprocessableError, match="diferente"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id, fuel_id=ETHANOL_ID))


def test_start_without_price_is_rejected(service: ShiftService, repos: dict, user: User) -> None:
    vehicle = add_vehicle(repos, user)

    with pytest.raises(ConflictError, match="Cadastre o preço"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id))


def test_start_with_shift_in_progress_is_rejected(
    service: ShiftService, repos: dict, user: User
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.200")
    service.start(user, ShiftStart(vehicle_id=vehicle.id))

    with pytest.raises(ConflictError, match="Já existe um expediente em andamento"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id))


def test_start_translates_unique_violation(service: ShiftService, repos: dict, user: User) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.200")
    repos["shifts"].fail_on_save = True

    with pytest.raises(ConflictError, match="Já existe um expediente em andamento"):
        service.start(user, ShiftStart(vehicle_id=vehicle.id))


def test_current_without_shift_is_not_found(service: ShiftService, user: User) -> None:
    with pytest.raises(NotFoundError, match="Nenhum expediente em andamento"):
        service.current(user)


def test_current_computes_partial_summary(
    service: ShiftService, repos: dict, user: User, clock: Clock
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.000")
    shift = service.start(user, ShiftStart(vehicle_id=vehicle.id)).shift
    repos["earnings"].earnings.append(
        Earning(shift_id=shift.id, amount=Decimal("20.00"), earned_at=NOW)
    )
    repos["track_points"].points += [
        TrackPoint(
            shift_id=shift.id, recorded_at=NOW + timedelta(minutes=5), latitude=0, longitude=0
        ),
        TrackPoint(
            shift_id=shift.id, recorded_at=NOW + timedelta(minutes=15), latitude=0, longitude=0
        ),
    ]
    clock.now = NOW + timedelta(hours=2)

    detail = service.current(user)

    assert detail.summary.earnings_total == Decimal("20.00")
    assert detail.summary.idle_minutes == 10
    assert detail.summary.fuel_cost == Decimal("0.14")
    assert detail.summary.duration_minutes == 120
    assert detail.last_point_at == NOW + timedelta(minutes=15)
    assert [gap.minutes for gap in detail.gaps] == [5, 10]


def test_finish_persists_metrics(
    service: ShiftService, repos: dict, user: User, clock: Clock
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.000")
    shift = service.start(user, ShiftStart(vehicle_id=vehicle.id)).shift
    repos["earnings"].earnings.append(
        Earning(shift_id=shift.id, amount=Decimal("100.00"), earned_at=NOW)
    )
    clock.now = NOW + timedelta(hours=4)

    detail = service.finish(user, shift.id)

    finished = repos["shifts"].shifts[shift.id]
    assert finished.status == ShiftStatus.FINISHED
    assert finished.ended_at == NOW + timedelta(hours=4)
    assert finished.earnings_total == Decimal("100.00")
    assert finished.profit == Decimal("100.00")
    assert finished.duration_minutes == 240
    assert finished.profit_per_hour == Decimal("25.00")
    assert finished.profit_per_km is None
    assert detail.summary.profit == finished.profit


def test_finished_shift_uses_stored_metrics_and_cannot_finish_again(
    service: ShiftService, repos: dict, user: User, clock: Clock
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.000")
    shift = service.start(user, ShiftStart(vehicle_id=vehicle.id)).shift
    clock.now = NOW + timedelta(hours=1)
    service.finish(user, shift.id)
    repos["earnings"].earnings.append(
        Earning(shift_id=shift.id, amount=Decimal("999.00"), earned_at=NOW)
    )
    clock.now = NOW + timedelta(hours=5)

    detail = service.get(user, shift.id)

    assert detail.summary.earnings_total == Decimal("0.00")
    assert detail.summary.duration_minutes == 60
    with pytest.raises(ConflictError, match="Expediente já encerrado"):
        service.finish(user, shift.id)


def test_get_shift_of_other_user_is_not_found(
    service: ShiftService, repos: dict, user: User
) -> None:
    vehicle = add_vehicle(repos, user)
    repos["prices"].prices[GASOLINE_ID] = Decimal("6.000")
    shift = service.start(user, ShiftStart(vehicle_id=vehicle.id)).shift

    with pytest.raises(NotFoundError, match="Expediente não encontrado"):
        service.get(User(id=uuid.uuid4()), shift.id)


def test_list_converts_local_dates_to_utc_range(
    service: ShiftService, repos: dict, user: User
) -> None:
    service.list_for_user(user, date(2026, 9, 19), date(2026, 9, 20), "America/Sao_Paulo", 2, 10)

    assert repos["shifts"].list_calls == [
        (
            user.id,
            datetime(2026, 9, 19, 3, 0, tzinfo=UTC),
            datetime(2026, 9, 21, 3, 0, tzinfo=UTC),
            10,
            10,
        )
    ]


def test_list_without_dates_has_open_range(service: ShiftService, repos: dict, user: User) -> None:
    service.list_for_user(user, None, None, "UTC", 1, 20)

    assert repos["shifts"].list_calls == [(user.id, None, None, 0, 20)]
