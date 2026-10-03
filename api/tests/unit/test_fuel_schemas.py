from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import ETHANOL_ID, GASOLINE_ID
from app.schemas.fuel import FuelPricesUpdate

pytestmark = pytest.mark.unit


def test_valid_update() -> None:
    data = FuelPricesUpdate(
        prices=[
            {"fuel_id": GASOLINE_ID, "price_per_liter": "6.20"},
            {"fuel_id": ETHANOL_ID, "price_per_liter": "3.759"},
        ]
    )

    assert [item.price_per_liter for item in data.prices] == [Decimal("6.20"), Decimal("3.759")]


@pytest.mark.parametrize("price", ["0", "-1.00", "6.2001", "1000.000"])
def test_invalid_price_is_rejected(price: str) -> None:
    with pytest.raises(ValidationError):
        FuelPricesUpdate(prices=[{"fuel_id": GASOLINE_ID, "price_per_liter": price}])


def test_empty_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FuelPricesUpdate(prices=[])


def test_repeated_fuel_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Combustível repetido"):
        FuelPricesUpdate(
            prices=[
                {"fuel_id": GASOLINE_ID, "price_per_liter": "6.20"},
                {"fuel_id": GASOLINE_ID, "price_per_liter": "6.30"},
            ]
        )
