import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from app.core.errors import NotFoundError, UnprocessableError
from app.models import Earning, Shift, User
from app.repositories.earning_repository import EarningRepository
from app.repositories.shift_repository import ShiftRepository
from app.schemas.earning import EarningCreate, EarningUpdate
from app.services.shift_access import get_open_shift, get_user_shift, within_shift

EARNING_NOT_FOUND = "Ganho não encontrado"
EARNED_AT_OUT_OF_SHIFT = "Horário do ganho fora do expediente"


class EarningService:
    def __init__(
        self,
        shifts: ShiftRepository,
        earnings: EarningRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.shifts = shifts
        self.earnings = earnings
        self.clock = clock

    def list_for_shift(self, user: User, shift_id: uuid.UUID) -> Sequence[Earning]:
        shift = get_user_shift(self.shifts, user, shift_id)
        return self.earnings.list_for_shift(shift.id)

    def add(self, user: User, shift_id: uuid.UUID, data: EarningCreate) -> Earning:
        shift = get_open_shift(self.shifts, user, shift_id)
        earned_at = data.earned_at or self.clock()
        self._ensure_within_shift(shift, earned_at)
        earning = Earning(
            shift_id=shift.id, amount=data.amount, platform=data.platform, earned_at=earned_at
        )
        return self.earnings.save(earning)

    def update(
        self, user: User, shift_id: uuid.UUID, earning_id: uuid.UUID, data: EarningUpdate
    ) -> Earning:
        shift = get_open_shift(self.shifts, user, shift_id)
        earning = self._earning(shift, earning_id)
        changes = data.model_dump(exclude_unset=True)
        if "earned_at" in changes:
            self._ensure_within_shift(shift, changes["earned_at"])
        for field, value in changes.items():
            setattr(earning, field, value)
        return self.earnings.save(earning)

    def delete(self, user: User, shift_id: uuid.UUID, earning_id: uuid.UUID) -> None:
        shift = get_open_shift(self.shifts, user, shift_id)
        self.earnings.delete(self._earning(shift, earning_id))

    def _earning(self, shift: Shift, earning_id: uuid.UUID) -> Earning:
        earning = self.earnings.get_for_shift(earning_id, shift.id)
        if earning is None:
            raise NotFoundError(EARNING_NOT_FOUND)
        return earning

    def _ensure_within_shift(self, shift: Shift, earned_at: datetime) -> None:
        if not within_shift(shift, earned_at, self.clock()):
            raise UnprocessableError(EARNED_AT_OUT_OF_SHIFT)
