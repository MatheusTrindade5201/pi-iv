import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models import User
from app.repositories.analytics_repository import DailyTotals, PeriodTotals
from app.schemas.analytics import AnalyticsQuery
from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.unit


class FakeAnalyticsRepository:
    def __init__(self, totals: PeriodTotals) -> None:
        self.totals = totals
        self.calls: list[tuple] = []

    def daily_totals(self, user_id, start, end, tz) -> list[DailyTotals]:
        self.calls.append(("daily", start, end, tz))
        return []

    def period_totals(self, user_id, start, end, tz) -> PeriodTotals:
        self.calls.append(("period", start, end, tz))
        return self.totals


def totals(**overrides: object) -> PeriodTotals:
    data = {
        "days_worked": 2,
        "shifts_count": 3,
        "earnings_total": Decimal("490.00"),
        "fuel_cost": Decimal("115.20"),
        "profit": Decimal("374.80"),
        "distance_km": Decimal("156.400"),
        "duration_minutes": 480,
        "idle_minutes": 60,
    }
    return PeriodTotals(**(data | overrides))


def query() -> AnalyticsQuery:
    return AnalyticsQuery.model_validate({"from": "2026-09-01", "to": "2026-09-30"})


def test_summary_recomputes_rates_from_totals() -> None:
    service = AnalyticsService(FakeAnalyticsRepository(totals()))

    result = service.summary(User(id=uuid.uuid4()), query())

    assert (result.date_from, result.date_to) == (date(2026, 9, 1), date(2026, 9, 30))
    assert result.profit_per_hour == Decimal("46.85")
    assert result.profit_per_km == Decimal("2.40")
    assert result.avg_profit_per_day == Decimal("187.40")


def test_empty_period_has_no_rates() -> None:
    empty = totals(
        days_worked=0,
        shifts_count=0,
        earnings_total=Decimal(0),
        fuel_cost=Decimal(0),
        profit=Decimal(0),
        distance_km=Decimal(0),
        duration_minutes=0,
        idle_minutes=0,
    )
    service = AnalyticsService(FakeAnalyticsRepository(empty))

    result = service.summary(User(id=uuid.uuid4()), query())

    assert result.profit_per_hour is None
    assert result.profit_per_km is None
    assert result.avg_profit_per_day is None


def test_queries_use_local_range_in_utc() -> None:
    repository = FakeAnalyticsRepository(totals())
    service = AnalyticsService(repository)

    service.daily(User(id=uuid.uuid4()), query())

    assert repository.calls == [
        (
            "daily",
            datetime(2026, 9, 1, 3, 0, tzinfo=UTC),
            datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
            "America/Sao_Paulo",
        )
    ]
