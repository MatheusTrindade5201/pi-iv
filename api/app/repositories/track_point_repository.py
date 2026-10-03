import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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

    def insert_ignoring_duplicates(self, shift_id: uuid.UUID, points: Iterable[dict]) -> int:
        rows = [{"id": uuid.uuid4(), "shift_id": shift_id, **point} for point in points]
        if not rows:
            return 0
        stmt = (
            insert(TrackPoint)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["shift_id", "recorded_at"])
            .returning(TrackPoint.id)
        )
        inserted = len(self.session.execute(stmt).all())
        self.session.commit()
        return inserted
