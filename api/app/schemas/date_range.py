from datetime import date
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_TZ = "America/Sao_Paulo"
DATES_OUT_OF_ORDER = "'from' deve ser anterior ou igual a 'to'"


class DateRangeQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    tz: str = DEFAULT_TZ

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
            raise ValueError(DATES_OUT_OF_ORDER)
        return self
