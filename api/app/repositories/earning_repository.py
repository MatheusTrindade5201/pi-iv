import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Earning


class EarningRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_shift(self, shift_id: uuid.UUID) -> Sequence[Earning]:
        return self.session.scalars(
            select(Earning)
            .where(Earning.shift_id == shift_id)
            .order_by(Earning.earned_at, Earning.id)
        ).all()

    def get_for_shift(self, earning_id: uuid.UUID, shift_id: uuid.UUID) -> Earning | None:
        return self.session.scalar(
            select(Earning).where(Earning.id == earning_id, Earning.shift_id == shift_id)
        )

    def save(self, earning: Earning) -> Earning:
        self.session.add(earning)
        self.session.commit()
        self.session.refresh(earning)
        return earning

    def delete(self, earning: Earning) -> None:
        self.session.delete(earning)
        self.session.commit()
