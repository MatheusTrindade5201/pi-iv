import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field

from app.models import Shift, ShiftStatus
from app.schemas.date_range import DateRangeQuery
from app.services.calculations import GpsGap, ShiftSummary


class ShiftStart(BaseModel):
    vehicle_id: uuid.UUID
    fuel_id: uuid.UUID | None = None


class ShiftListQuery(DateRangeQuery):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


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
