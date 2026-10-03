from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

MAX_BATCH_SIZE = 500


def _rounded(places: int) -> AfterValidator:
    step = Decimal(1).scaleb(-places)
    return AfterValidator(lambda value: value.quantize(step, rounding=ROUND_HALF_UP))


Latitude = Annotated[Decimal, Field(ge=-90, le=90), _rounded(6)]
Longitude = Annotated[Decimal, Field(ge=-180, le=180), _rounded(6)]
AccuracyM = Annotated[Decimal, Field(ge=0, lt=100000), _rounded(2)]
SpeedMs = Annotated[Decimal, Field(ge=0, lt=10000), _rounded(2)]


class TrackPointInput(BaseModel):
    recorded_at: AwareDatetime
    latitude: Latitude
    longitude: Longitude
    accuracy_m: AccuracyM | None = None
    speed_ms: SpeedMs | None = None


class TrackPointBatch(BaseModel):
    points: list[TrackPointInput] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


class TrackPointBatchResult(BaseModel):
    accepted: int
    duplicated: int
    rejected: int


class TrackPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorded_at: datetime
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal | None
    speed_ms: Decimal | None
