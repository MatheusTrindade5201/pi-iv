from datetime import date, timedelta
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.date_range import DATES_OUT_OF_ORDER, DateRangeQuery
from app.services.date_range import local_today

DEFAULT_PERIOD_DAYS = 30
MAX_PERIOD_DAYS = 366


class AnalyticsQuery(DateRangeQuery):
    @model_validator(mode="after")
    def default_period(self) -> Self:
        if self.date_to is None:
            self.date_to = local_today(self.tz)
        if self.date_from is None:
            self.date_from = self.date_to - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
        if self.date_from > self.date_to:
            raise ValueError(DATES_OUT_OF_ORDER)
        if (self.date_to - self.date_from).days + 1 > MAX_PERIOD_DAYS:
            raise ValueError(f"O período deve ter no máximo {MAX_PERIOD_DAYS} dias")
        return self


class TotalsResponse(BaseModel):
    shifts_count: int
    earnings_total: Decimal
    fuel_cost: Decimal
    profit: Decimal
    distance_km: Decimal
    duration_minutes: int
    idle_minutes: int


class DailyTotalsResponse(TotalsResponse):
    date: date


class PeriodSummaryResponse(TotalsResponse):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    date_from: date = Field(alias="from")
    date_to: date = Field(alias="to")
    days_worked: int
    profit_per_hour: Decimal | None
    profit_per_km: Decimal | None
    avg_profit_per_day: Decimal | None
