import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import Earning, Shift, ShiftStatus, User
from app.schemas.earning import EarningCreate, EarningUpdate
from app.services.earning_service import EarningService

pytestmark = pytest.mark.unit

STARTED_AT = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
NOW = STARTED_AT + timedelta(hours=2)


class FakeShiftRepository:
    def __init__(self) -> None:
        self.shifts: dict[uuid.UUID, Shift] = {}

    def get_for_user(self, shift_id: uuid.UUID, user_id: uuid.UUID) -> Shift | None:
        shift = self.shifts.get(shift_id)
        return shift if shift is not None and shift.user_id == user_id else None


class FakeEarningRepository:
    def __init__(self) -> None:
        self.earnings: dict[uuid.UUID, Earning] = {}

    def list_for_shift(self, shift_id: uuid.UUID) -> list[Earning]:
        return sorted(
            (e for e in self.earnings.values() if e.shift_id == shift_id),
            key=lambda e: e.earned_at,
        )

    def get_for_shift(self, earning_id: uuid.UUID, shift_id: uuid.UUID) -> Earning | None:
        earning = self.earnings.get(earning_id)
        return earning if earning is not None and earning.shift_id == shift_id else None

    def save(self, earning: Earning) -> Earning:
        earning.id = earning.id or uuid.uuid4()
        self.earnings[earning.id] = earning
        return earning

    def delete(self, earning: Earning) -> None:
        del self.earnings[earning.id]


@pytest.fixture
def shifts() -> FakeShiftRepository:
    return FakeShiftRepository()


@pytest.fixture
def earnings() -> FakeEarningRepository:
    return FakeEarningRepository()


@pytest.fixture
def service(shifts: FakeShiftRepository, earnings: FakeEarningRepository) -> EarningService:
    return EarningService(shifts=shifts, earnings=earnings, clock=lambda: NOW)


@pytest.fixture
def user() -> User:
    return User(id=uuid.uuid4())


def add_shift(
    shifts: FakeShiftRepository, user: User, status: ShiftStatus = ShiftStatus.IN_PROGRESS
) -> Shift:
    shift = Shift(id=uuid.uuid4(), user_id=user.id, started_at=STARTED_AT, status=status)
    shifts.shifts[shift.id] = shift
    return shift


def test_add_defaults_earned_at_to_now(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    earning = service.add(user, shift.id, EarningCreate(amount="20", platform="iFood"))

    assert earning.shift_id == shift.id
    assert earning.amount == Decimal("20")
    assert earning.platform == "iFood"
    assert earning.earned_at == NOW


@pytest.mark.parametrize(
    "earned_at",
    [STARTED_AT - timedelta(seconds=1), NOW + timedelta(minutes=2)],
)
def test_add_rejects_earned_at_outside_shift(
    service: EarningService, shifts: FakeShiftRepository, user: User, earned_at: datetime
) -> None:
    shift = add_shift(shifts, user)

    with pytest.raises(UnprocessableError, match="fora do expediente"):
        service.add(user, shift.id, EarningCreate(amount="20", earned_at=earned_at))


def test_add_accepts_small_clock_skew(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)
    earned_at = NOW + timedelta(seconds=30)

    assert (
        service.add(user, shift.id, EarningCreate(amount="5", earned_at=earned_at)).earned_at
        == earned_at
    )


def test_finished_shift_is_read_only(
    service: EarningService,
    shifts: FakeShiftRepository,
    earnings: FakeEarningRepository,
    user: User,
) -> None:
    shift = add_shift(shifts, user, ShiftStatus.FINISHED)
    earning = earnings.save(Earning(shift_id=shift.id, amount=Decimal("10"), earned_at=STARTED_AT))

    with pytest.raises(ConflictError, match="Expediente já encerrado"):
        service.add(user, shift.id, EarningCreate(amount="5"))
    with pytest.raises(ConflictError):
        service.update(user, shift.id, earning.id, EarningUpdate(amount="7"))
    with pytest.raises(ConflictError):
        service.delete(user, shift.id, earning.id)
    assert service.list_for_shift(user, shift.id) == [earning]


def test_shift_of_other_user_is_not_found(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, User(id=uuid.uuid4()))

    with pytest.raises(NotFoundError, match="Expediente não encontrado"):
        service.add(user, shift.id, EarningCreate(amount="5"))
    with pytest.raises(NotFoundError):
        service.list_for_shift(user, shift.id)


def test_earning_of_other_shift_is_not_found(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)
    other_shift = add_shift(shifts, user)
    earning = service.add(user, other_shift.id, EarningCreate(amount="5"))

    with pytest.raises(NotFoundError, match="Ganho não encontrado"):
        service.update(user, shift.id, earning.id, EarningUpdate(amount="7"))
    with pytest.raises(NotFoundError):
        service.delete(user, shift.id, earning.id)


def test_update_is_partial_and_validates_earned_at(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)
    earning = service.add(user, shift.id, EarningCreate(amount="20", platform="iFood"))

    updated = service.update(user, shift.id, earning.id, EarningUpdate(amount="12"))

    assert updated.amount == Decimal("12")
    assert updated.platform == "iFood"
    assert updated.earned_at == NOW
    with pytest.raises(UnprocessableError):
        service.update(
            user, shift.id, earning.id, EarningUpdate(earned_at=STARTED_AT - timedelta(hours=1))
        )


def test_delete_removes_earning(
    service: EarningService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)
    earning = service.add(user, shift.id, EarningCreate(amount="20"))

    service.delete(user, shift.id, earning.id)

    assert service.list_for_shift(user, shift.id) == []
