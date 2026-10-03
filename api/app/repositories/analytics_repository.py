import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, cast, distinct, func, select
from sqlalchemy.orm import Session

from app.models import Shift, ShiftStatus


@dataclass(frozen=True)
class Totals:
    shifts_count: int
    earnings_total: Decimal
    fuel_cost: Decimal
    profit: Decimal
    distance_km: Decimal
    duration_minutes: int
    idle_minutes: int


@dataclass(frozen=True)
class DailyTotals(Totals):
    day: date


@dataclass(frozen=True)
class PeriodTotals(Totals):
    days_worked: int


def _sum(column, zero: object = 0):
    return func.coalesce(func.sum(column), zero)


def _total_columns() -> list:
    return [
        func.count(Shift.id),
        _sum(Shift.earnings_total, Decimal(0)),
        _sum(Shift.fuel_cost, Decimal(0)),
        _sum(Shift.profit, Decimal(0)),
        _sum(Shift.distance_km, Decimal(0)),
        _sum(Shift.duration_minutes),
        _sum(Shift.idle_minutes),
    ]


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def daily_totals(
        self, user_id: uuid.UUID, start: datetime, end: datetime, tz: str
    ) -> list[DailyTotals]:
        day = self._local_day(tz)
        stmt = (
            self._finished(select(day, *_total_columns()), user_id, start, end)
            .group_by(day)
            .order_by(day.desc())
        )
        return [
            DailyTotals(
                day=row[0],
                shifts_count=row[1],
                earnings_total=row[2],
                fuel_cost=row[3],
                profit=row[4],
                distance_km=row[5],
                duration_minutes=int(row[6]),
                idle_minutes=int(row[7]),
            )
            for row in self.session.execute(stmt).all()
        ]

    def period_totals(
        self, user_id: uuid.UUID, start: datetime, end: datetime, tz: str
    ) -> PeriodTotals:
        stmt = self._finished(
            select(func.count(distinct(self._local_day(tz))), *_total_columns()),
            user_id,
            start,
            end,
        )
        row = self.session.execute(stmt).one()
        return PeriodTotals(
            days_worked=row[0],
            shifts_count=row[1],
            earnings_total=row[2],
            fuel_cost=row[3],
            profit=row[4],
            distance_km=row[5],
            duration_minutes=int(row[6]),
            idle_minutes=int(row[7]),
        )

    @staticmethod
    def _local_day(tz: str):
        return cast(func.timezone(tz, Shift.started_at), Date)

    @staticmethod
    def _finished(stmt, user_id: uuid.UUID, start: datetime, end: datetime):
        return stmt.where(
            Shift.user_id == user_id,
            Shift.status == ShiftStatus.FINISHED,
            Shift.started_at >= start,
            Shift.started_at < end,
        )
