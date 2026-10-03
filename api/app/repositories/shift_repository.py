import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Shift, ShiftStatus


class ShiftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_user(self, shift_id: uuid.UUID, user_id: uuid.UUID) -> Shift | None:
        return self.session.scalar(
            select(Shift).where(Shift.id == shift_id, Shift.user_id == user_id)
        )

    def get_in_progress(self, user_id: uuid.UUID) -> Shift | None:
        return self.session.scalar(
            select(Shift).where(Shift.user_id == user_id, Shift.status == ShiftStatus.IN_PROGRESS)
        )

    def list_for_user(
        self,
        user_id: uuid.UUID,
        start: datetime | None,
        end: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Shift], int]:
        stmt = self._filtered(select(Shift), user_id, start, end)
        total = self.session.scalar(
            self._filtered(select(func.count()).select_from(Shift), user_id, start, end)
        )
        items = self.session.scalars(
            stmt.order_by(Shift.started_at.desc(), Shift.id).offset(offset).limit(limit)
        ).all()
        return items, total or 0

    def save(self, shift: Shift) -> Shift:
        self.session.add(shift)
        self.session.commit()
        self.session.refresh(shift)
        return shift

    def rollback(self) -> None:
        self.session.rollback()

    @staticmethod
    def _filtered(
        stmt: Select, user_id: uuid.UUID, start: datetime | None, end: datetime | None
    ) -> Select:
        stmt = stmt.where(Shift.user_id == user_id)
        if start is not None:
            stmt = stmt.where(Shift.started_at >= start)
        if end is not None:
            stmt = stmt.where(Shift.started_at < end)
        return stmt
