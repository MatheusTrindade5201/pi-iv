from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models import User
from app.repositories.analytics_repository import AnalyticsRepository, DailyTotals, PeriodTotals
from app.schemas.analytics import AnalyticsQuery
from app.services.calculations import per_hour, per_km
from app.services.date_range import local_range_to_utc


@dataclass(frozen=True)
class PeriodSummary:
    date_from: date
    date_to: date
    totals: PeriodTotals
    profit_per_hour: Decimal | None
    profit_per_km: Decimal | None
    avg_profit_per_day: Decimal | None


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def daily(self, user: User, query: AnalyticsQuery) -> list[DailyTotals]:
        start, end = local_range_to_utc(query.date_from, query.date_to, query.tz)
        return self.repository.daily_totals(user.id, start, end, query.tz)

    def summary(self, user: User, query: AnalyticsQuery) -> PeriodSummary:
        start, end = local_range_to_utc(query.date_from, query.date_to, query.tz)
        totals = self.repository.period_totals(user.id, start, end, query.tz)
        return PeriodSummary(
            date_from=query.date_from,
            date_to=query.date_to,
            totals=totals,
            profit_per_hour=per_hour(totals.profit, totals.duration_minutes),
            profit_per_km=per_km(totals.profit, totals.distance_km),
            avg_profit_per_day=_average(totals.profit, totals.days_worked),
        )


def _average(value: Decimal, count: int) -> Decimal | None:
    if not count:
        return None
    return (value / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
