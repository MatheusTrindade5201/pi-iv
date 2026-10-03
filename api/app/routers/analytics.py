from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import AnalyticsServiceDep, CurrentUser
from app.repositories.analytics_repository import Totals
from app.schemas.analytics import AnalyticsQuery, DailyTotalsResponse, PeriodSummaryResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


def totals_fields(totals: Totals) -> dict:
    return {
        "shifts_count": totals.shifts_count,
        "earnings_total": totals.earnings_total,
        "fuel_cost": totals.fuel_cost,
        "profit": totals.profit,
        "distance_km": totals.distance_km,
        "duration_minutes": totals.duration_minutes,
        "idle_minutes": totals.idle_minutes,
    }


@router.get("/daily", response_model=list[DailyTotalsResponse])
def daily(
    query: Annotated[AnalyticsQuery, Query()], user: CurrentUser, service: AnalyticsServiceDep
) -> list[DailyTotalsResponse]:
    return [
        DailyTotalsResponse(date=totals.day, **totals_fields(totals))
        for totals in service.daily(user, query)
    ]


@router.get("/summary", response_model=PeriodSummaryResponse)
def summary(
    query: Annotated[AnalyticsQuery, Query()], user: CurrentUser, service: AnalyticsServiceDep
) -> PeriodSummaryResponse:
    result = service.summary(user, query)
    return PeriodSummaryResponse(
        date_from=result.date_from,
        date_to=result.date_to,
        days_worked=result.totals.days_worked,
        profit_per_hour=result.profit_per_hour,
        profit_per_km=result.profit_per_km,
        avg_profit_per_day=result.avg_profit_per_day,
        **totals_fields(result.totals),
    )
