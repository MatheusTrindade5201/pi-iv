import pytest

from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, Base, ShiftStatus
from app.models.base import NAMING_CONVENTION
from app.models.fuel import SEED_FUELS

pytestmark = pytest.mark.unit


def test_shift_status_values() -> None:
    assert [status.value for status in ShiftStatus] == ["in_progress", "finished"]


def test_seed_fuels_have_distinct_fixed_ids() -> None:
    assert len({GASOLINE_ID, ETHANOL_ID, FLEX_ID}) == 3
    assert SEED_FUELS == {GASOLINE_ID: "Gasolina", ETHANOL_ID: "Etanol", FLEX_ID: "Flex"}


def test_metadata_uses_naming_convention() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION


def test_metadata_contains_all_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "fuel",
        "fuel_prices",
        "vehicles",
        "shifts",
        "earnings",
        "track_points",
    }
