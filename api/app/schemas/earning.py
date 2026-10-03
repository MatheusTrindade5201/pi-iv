import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Amount = Annotated[Decimal, Field(gt=0, le=100000, max_digits=10, decimal_places=2)]
Platform = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
REQUIRED_FIELDS = ("amount", "earned_at")


class EarningCreate(BaseModel):
    amount: Amount
    platform: Platform | None = None
    earned_at: AwareDatetime | None = None


class EarningUpdate(BaseModel):
    amount: Amount | None = None
    platform: Platform | None = None
    earned_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def required_fields_not_null(self) -> Self:
        for field in REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} não pode ser nulo")
        return self


class EarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shift_id: uuid.UUID
    amount: Decimal
    platform: str | None
    earned_at: datetime
