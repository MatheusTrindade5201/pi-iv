from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import FLEX_ID, GASOLINE_ID
from app.schemas.vehicle import VehicleCreate, VehicleUpdate

pytestmark = pytest.mark.unit

NEXT_YEAR = datetime.now(UTC).year + 1


def create_data(**overrides: object) -> dict[str, object]:
    return {"model": "Honda CG 160", "fuel_id": GASOLINE_ID, "declared_kml": "32"} | overrides


def test_minimal_vehicle_is_valid() -> None:
    vehicle = VehicleCreate(**create_data(model="  Honda  "))

    assert vehicle.model == "Honda"
    assert vehicle.declared_kml == Decimal("32")
    assert vehicle.displacement_cc is None
    assert vehicle.year is None


def test_complete_vehicle_is_valid() -> None:
    vehicle = VehicleCreate(
        **create_data(fuel_id=FLEX_ID, declared_kml="35.50", displacement_cc=160, year=NEXT_YEAR)
    )

    assert vehicle.displacement_cc == 160
    assert vehicle.year == NEXT_YEAR


@pytest.mark.parametrize(
    "overrides",
    [
        {"model": "  "},
        {"model": "x" * 121},
        {"declared_kml": "0"},
        {"declared_kml": "-10"},
        {"declared_kml": "32.555"},
        {"declared_kml": "1000"},
        {"displacement_cc": 0},
        {"displacement_cc": 3001},
        {"year": 1949},
        {"year": NEXT_YEAR + 1},
    ],
)
def test_invalid_vehicle_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        VehicleCreate(**create_data(**overrides))


@pytest.mark.parametrize("field", ["model", "fuel_id", "declared_kml"])
def test_update_rejects_null_on_required_field(field: str) -> None:
    with pytest.raises(ValidationError, match="não pode ser nulo"):
        VehicleUpdate(**{field: None})


def test_update_accepts_null_on_optional_fields() -> None:
    update = VehicleUpdate(year=None, displacement_cc=None)

    assert update.model_dump(exclude_unset=True) == {"year": None, "displacement_cc": None}


def test_update_only_includes_sent_fields() -> None:
    assert VehicleUpdate(declared_kml="30").model_dump(exclude_unset=True) == {
        "declared_kml": Decimal("30")
    }
