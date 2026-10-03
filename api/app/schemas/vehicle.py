import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator

from app.models import Vehicle

MIN_YEAR = 1950
REQUIRED_FIELDS = ("model", "fuel_id", "declared_kml")


def _not_in_future(year: int) -> int:
    max_year = datetime.now(UTC).year + 1
    if year > max_year:
        raise ValueError(f"Ano deve ser no máximo {max_year}")
    return year


Model = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Kml = Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=2)]
DisplacementCc = Annotated[int, Field(ge=1, le=3000)]
Year = Annotated[int, Field(ge=MIN_YEAR), AfterValidator(_not_in_future)]


class VehicleCreate(BaseModel):
    model: Model
    fuel_id: uuid.UUID
    declared_kml: Kml
    displacement_cc: DisplacementCc | None = None
    year: Year | None = None


class VehicleUpdate(BaseModel):
    model: Model | None = None
    fuel_id: uuid.UUID | None = None
    declared_kml: Kml | None = None
    displacement_cc: DisplacementCc | None = None
    year: Year | None = None

    @model_validator(mode="after")
    def required_fields_not_null(self) -> Self:
        for field in REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} não pode ser nulo")
        return self


class VehicleResponse(BaseModel):
    id: uuid.UUID
    model: str
    fuel_id: uuid.UUID
    fuel_name: str
    declared_kml: Decimal
    displacement_cc: int | None
    year: int | None
    created_at: datetime

    @classmethod
    def from_model(cls, vehicle: Vehicle) -> Self:
        return cls(
            id=vehicle.id,
            model=vehicle.model,
            fuel_id=vehicle.fuel_id,
            fuel_name=vehicle.fuel.name,
            declared_kml=vehicle.declared_kml,
            displacement_cc=vehicle.displacement_cc,
            year=vehicle.year,
            created_at=vehicle.created_at,
        )
