import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import FuelPrice

PricePerLiter = Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=3)]


class FuelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class FuelPriceInput(BaseModel):
    fuel_id: uuid.UUID
    price_per_liter: PricePerLiter


class FuelPricesUpdate(BaseModel):
    prices: list[FuelPriceInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_fuels(self) -> Self:
        fuel_ids = [price.fuel_id for price in self.prices]
        if len(fuel_ids) != len(set(fuel_ids)):
            raise ValueError("Combustível repetido na lista de preços")
        return self


class FuelPriceResponse(BaseModel):
    fuel_id: uuid.UUID
    fuel_name: str
    price_per_liter: Decimal
    valid_from: datetime

    @classmethod
    def from_model(cls, price: FuelPrice) -> Self:
        return cls(
            fuel_id=price.fuel_id,
            fuel_name=price.fuel.name,
            price_per_liter=price.price_per_liter,
            valid_from=price.valid_from,
        )
