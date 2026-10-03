import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.models import Shift, ShiftStatus, TrackPoint, User
from app.schemas.track_point import TrackPointBatch
from app.services.track_point_service import TrackPointService

pytestmark = pytest.mark.unit

STARTED_AT = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
NOW = STARTED_AT + timedelta(hours=1)


class FakeShiftRepository:
    def __init__(self) -> None:
        self.shifts: dict[uuid.UUID, Shift] = {}

    def get_for_user(self, shift_id: uuid.UUID, user_id: uuid.UUID) -> Shift | None:
        shift = self.shifts.get(shift_id)
        return shift if shift is not None and shift.user_id == user_id else None


class FakeTrackPointRepository:
    def __init__(self) -> None:
        self.points: dict[tuple[uuid.UUID, datetime], dict] = {}

    def list_for_shift(self, shift_id: uuid.UUID) -> list[TrackPoint]:
        return [
            TrackPoint(shift_id=shift_id, **point)
            for (sid, _), point in sorted(self.points.items(), key=lambda item: item[0][1])
            if sid == shift_id
        ]

    def insert_ignoring_duplicates(self, shift_id: uuid.UUID, points: Iterable[dict]) -> int:
        inserted = 0
        for point in points:
            key = (shift_id, point["recorded_at"])
            if key not in self.points:
                self.points[key] = point
                inserted += 1
        return inserted


@pytest.fixture
def shifts() -> FakeShiftRepository:
    return FakeShiftRepository()


@pytest.fixture
def track_points() -> FakeTrackPointRepository:
    return FakeTrackPointRepository()


@pytest.fixture
def service(
    shifts: FakeShiftRepository, track_points: FakeTrackPointRepository
) -> TrackPointService:
    return TrackPointService(shifts=shifts, track_points=track_points, clock=lambda: NOW)


@pytest.fixture
def user() -> User:
    return User(id=uuid.uuid4())


def add_shift(
    shifts: FakeShiftRepository, user: User, status: ShiftStatus = ShiftStatus.IN_PROGRESS
) -> Shift:
    shift = Shift(id=uuid.uuid4(), user_id=user.id, started_at=STARTED_AT, status=status)
    shifts.shifts[shift.id] = shift
    return shift


def batch(*minutes: float) -> TrackPointBatch:
    return TrackPointBatch(
        points=[
            {
                "recorded_at": STARTED_AT + timedelta(minutes=minute),
                "latitude": -23.55,
                "longitude": -46.63,
            }
            for minute in minutes
        ]
    )


def test_batch_is_accepted(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    result = service.add_batch(user, shift.id, batch(1, 2, 3))

    assert (result.accepted, result.duplicated, result.rejected) == (3, 0, 0)
    assert len(service.list_for_shift(user, shift.id)) == 3


def test_resending_batch_counts_duplicates(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)
    service.add_batch(user, shift.id, batch(1, 2))

    result = service.add_batch(user, shift.id, batch(1, 2, 3))

    assert (result.accepted, result.duplicated, result.rejected) == (1, 2, 0)


def test_repeated_point_in_same_batch_is_duplicate(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    result = service.add_batch(user, shift.id, batch(1, 1, 2))

    assert (result.accepted, result.duplicated, result.rejected) == (2, 1, 0)


def test_points_outside_shift_are_rejected(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    result = service.add_batch(user, shift.id, batch(-1, 30, 62))

    assert (result.accepted, result.duplicated, result.rejected) == (1, 0, 2)


def test_point_within_clock_tolerance_is_accepted(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    assert service.add_batch(user, shift.id, batch(60.5)).accepted == 1


def test_batch_with_only_rejected_points(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user)

    result = service.add_batch(user, shift.id, batch(-5, -2))

    assert (result.accepted, result.duplicated, result.rejected) == (0, 0, 2)
    assert service.list_for_shift(user, shift.id) == []


def test_finished_shift_rejects_points(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, user, ShiftStatus.FINISHED)

    with pytest.raises(ConflictError, match="Expediente já encerrado"):
        service.add_batch(user, shift.id, batch(1))
    assert service.list_for_shift(user, shift.id) == []


def test_shift_of_other_user_is_not_found(
    service: TrackPointService, shifts: FakeShiftRepository, user: User
) -> None:
    shift = add_shift(shifts, User(id=uuid.uuid4()))

    with pytest.raises(NotFoundError, match="Expediente não encontrado"):
        service.add_batch(user, shift.id, batch(1))
    with pytest.raises(NotFoundError):
        service.list_for_shift(user, shift.id)
