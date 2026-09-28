from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Earning, ShiftStatus, TrackPoint
from tests.factories import (
    make_earning,
    make_shift,
    make_track_point,
    make_user,
    make_vehicle,
)

pytestmark = pytest.mark.integration


def test_duplicate_email_is_rejected(db_session: Session) -> None:
    make_user(db_session, email="john@example.com")

    with pytest.raises(IntegrityError):
        make_user(db_session, email="john@example.com")


def test_only_one_shift_in_progress_per_user(db_session: Session) -> None:
    user = make_user(db_session)
    vehicle = make_vehicle(db_session, user)
    make_shift(db_session, user, vehicle)

    with pytest.raises(IntegrityError):
        make_shift(db_session, user, vehicle)


def test_finished_shift_does_not_block_new_shift(db_session: Session) -> None:
    user = make_user(db_session)
    vehicle = make_vehicle(db_session, user)
    make_shift(db_session, user, vehicle, status=ShiftStatus.FINISHED, ended_at=datetime.now(UTC))

    shift = make_shift(db_session, user, vehicle)

    assert shift.status == ShiftStatus.IN_PROGRESS


def test_shifts_in_progress_of_different_users_are_allowed(db_session: Session) -> None:
    for _ in range(2):
        user = make_user(db_session)
        make_shift(db_session, user, make_vehicle(db_session, user))


def test_duplicate_track_point_timestamp_is_rejected(db_session: Session) -> None:
    user = make_user(db_session)
    shift = make_shift(db_session, user, make_vehicle(db_session, user))
    recorded_at = datetime.now(UTC)
    make_track_point(db_session, shift, recorded_at=recorded_at)

    with pytest.raises(IntegrityError):
        make_track_point(db_session, shift, recorded_at=recorded_at)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5.00")])
def test_non_positive_earning_is_rejected(db_session: Session, amount: Decimal) -> None:
    user = make_user(db_session)
    shift = make_shift(db_session, user, make_vehicle(db_session, user))

    with pytest.raises(IntegrityError):
        make_earning(db_session, shift, amount=amount)


@pytest.mark.parametrize(
    ("field", "value"), [("latitude", Decimal("91")), ("longitude", Decimal("-181"))]
)
def test_out_of_range_coordinates_are_rejected(
    db_session: Session, field: str, value: Decimal
) -> None:
    user = make_user(db_session)
    shift = make_shift(db_session, user, make_vehicle(db_session, user))

    with pytest.raises(IntegrityError):
        make_track_point(db_session, shift, **{field: value})


def test_non_positive_declared_kml_is_rejected(db_session: Session) -> None:
    user = make_user(db_session)

    with pytest.raises(IntegrityError):
        make_vehicle(db_session, user, declared_kml=Decimal("0"))


def test_deleting_shift_cascades_to_earnings_and_track_points(db_session: Session) -> None:
    user = make_user(db_session)
    shift = make_shift(db_session, user, make_vehicle(db_session, user))
    make_earning(db_session, shift)
    make_track_point(db_session, shift)

    db_session.delete(shift)
    db_session.flush()

    assert db_session.scalar(select(func.count()).select_from(Earning)) == 0
    assert db_session.scalar(select(func.count()).select_from(TrackPoint)) == 0
