import uuid
from datetime import datetime, timedelta

from app.core.errors import ConflictError, NotFoundError
from app.models import Shift, ShiftStatus, User
from app.repositories.shift_repository import ShiftRepository

SHIFT_NOT_FOUND = "Expediente não encontrado"
SHIFT_ALREADY_FINISHED = "Expediente já encerrado"
CLOCK_TOLERANCE = timedelta(minutes=1)


def get_user_shift(shifts: ShiftRepository, user: User, shift_id: uuid.UUID) -> Shift:
    shift = shifts.get_for_user(shift_id, user.id)
    if shift is None:
        raise NotFoundError(SHIFT_NOT_FOUND)
    return shift


def get_open_shift(shifts: ShiftRepository, user: User, shift_id: uuid.UUID) -> Shift:
    shift = get_user_shift(shifts, user, shift_id)
    if shift.status == ShiftStatus.FINISHED:
        raise ConflictError(SHIFT_ALREADY_FINISHED)
    return shift


def within_shift(shift: Shift, instant: datetime, now: datetime) -> bool:
    return shift.started_at <= instant <= now + CLOCK_TOLERANCE
