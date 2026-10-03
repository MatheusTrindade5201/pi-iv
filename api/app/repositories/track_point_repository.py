import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TrackPoint


class TrackPointRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_shift(self, shift_id: uuid.UUID) -> Sequence[TrackPoint]:
        return self.session.scalars(
            select(TrackPoint)
            .where(TrackPoint.shift_id == shift_id)
            .order_by(TrackPoint.recorded_at)
        ).all()
