import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Shift, ShiftStatus
from app.services.calculations import GpsGap, ShiftSummary


class ShiftStart(BaseModel):
    vehicle_id: uuid.UUID
    fuel_id: uuid.UUID | None = None


class ShiftListQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    tz: str = "America/Sao_Paulo"
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @field_validator("tz")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Fuso horário inválido") from exc
        return value

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("'from' deve ser anterior ou igual a 'to'")
        return self


class ShiftSummaryResponse(BaseModel):
    earnings_total: Decimal
    fuel_cost: Decimal
    profit: Decimal
    distance_km: Decimal
    duration_minutes: int
    idle_minutes: int
    profit_per_hour: Decimal | None
    profit_per_km: Decimal | None

    @classmethod
    def from_summary(cls, summary: ShiftSummary) -> Self:
        return cls(
            earnings_total=summary.earnings_total,
            fuel_cost=summary.fuel_cost,
            profit=summary.profit,
            distance_km=summary.distance_km,
            duration_minutes=summary.duration_minutes,
            idle_minutes=summary.idle_minutes,
            profit_per_hour=summary.profit_per_hour,
            profit_per_km=summary.profit_per_km,
        )


class GpsGapResponse(BaseModel):
    start: datetime
    end: datetime
    minutes: int

    @classmethod
    def from_gap(cls, gap: GpsGap) -> Self:
        return cls(start=gap.start, end=gap.end, minutes=gap.minutes)


class GpsStatusResponse(BaseModel):
    last_point_at: datetime | None
    gaps: list[GpsGapResponse]


class ShiftBase(BaseModel):
    id: uuid.UUID
    status: ShiftStatus
    vehicle_id: uuid.UUID
    fuel_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    price_per_liter_used: Decimal
    kml_used: Decimal


class ShiftResponse(ShiftBase):
    summary: ShiftSummaryResponse
    gps: GpsStatusResponse


class ShiftListItem(ShiftBase):
    summary: ShiftSummaryResponse | None


class ShiftPage(BaseModel):
    items: list[ShiftListItem]
    total: int
    page: int
    size: int


def shift_fields(shift: Shift) -> dict:
    return {
        "id": shift.id,
        "status": shift.status,
        "vehicle_id": shift.vehicle_id,
        "fuel_id": shift.fuel_id,
        "started_at": shift.started_at,
        "ended_at": shift.ended_at,
        "price_per_liter_used": shift.price_per_liter_used,
        "kml_used": shift.kml_used,
    }
