import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Shift, ShiftStatus
from app.repositories.shift_repository import ShiftRepository
from tests.factories import make_user, make_vehicle

pytestmark = pytest.mark.integration


def test_rollback_after_second_shift_in_progress_keeps_session_usable(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    vehicle = make_vehicle(db_session, user)
    repository = ShiftRepository(db_session)

    def new_shift() -> Shift:
        return Shift(
            user_id=user.id,
            vehicle_id=vehicle.id,
            fuel_id=vehicle.fuel_id,
            started_at=vehicle.created_at,
            status=ShiftStatus.IN_PROGRESS,
            price_per_liter_used=6,
            kml_used=vehicle.declared_kml,
        )

    first = repository.save(new_shift())
    with pytest.raises(IntegrityError):
        repository.save(new_shift())
    repository.rollback()

    assert repository.get_in_progress(user.id).id == first.id
