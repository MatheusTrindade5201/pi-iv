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
