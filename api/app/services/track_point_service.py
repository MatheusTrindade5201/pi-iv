import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import TrackPoint, User
from app.repositories.shift_repository import ShiftRepository
from app.repositories.track_point_repository import TrackPointRepository
from app.schemas.track_point import TrackPointBatch
from app.services.shift_access import get_open_shift, get_user_shift, within_shift


@dataclass(frozen=True)
class BatchResult:
    accepted: int
    duplicated: int
    rejected: int


class TrackPointService:
    def __init__(
        self,
        shifts: ShiftRepository,
        track_points: TrackPointRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.shifts = shifts
        self.track_points = track_points
        self.clock = clock

    def list_for_shift(self, user: User, shift_id: uuid.UUID) -> Sequence[TrackPoint]:
        shift = get_user_shift(self.shifts, user, shift_id)
        return self.track_points.list_for_shift(shift.id)

    def add_batch(self, user: User, shift_id: uuid.UUID, data: TrackPointBatch) -> BatchResult:
        shift = get_open_shift(self.shifts, user, shift_id)
        now = self.clock()

        valid: dict[datetime, dict] = {}
        rejected = 0
        for point in data.points:
            if not within_shift(shift, point.recorded_at, now):
                rejected += 1
                continue
            valid.setdefault(point.recorded_at, point.model_dump())

        accepted = self.track_points.insert_ignoring_duplicates(shift.id, valid.values())
        duplicated = len(data.points) - rejected - accepted
        return BatchResult(accepted=accepted, duplicated=duplicated, rejected=rejected)
