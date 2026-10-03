from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.earning import EarningCreate, EarningUpdate

pytestmark = pytest.mark.unit


def test_minimal_earning_is_valid() -> None:
    earning = EarningCreate(amount="20")

    assert earning.amount == Decimal("20")
    assert earning.platform is None
    assert earning.earned_at is None


def test_platform_is_trimmed() -> None:
    assert EarningCreate(amount="5", platform="  iFood ").platform == "iFood"


@pytest.mark.parametrize(
    "data",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "5.001"},
        {"amount": "100000.01"},
        {"amount": "5", "platform": "  "},
        {"amount": "5", "platform": "x" * 51},
        {"amount": "5", "earned_at": "2026-09-20T10:00:00"},
    ],
)
def test_invalid_earning_is_rejected(data: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        EarningCreate(**data)


@pytest.mark.parametrize("field", ["amount", "earned_at"])
def test_update_rejects_null_on_required_field(field: str) -> None:
    with pytest.raises(ValidationError, match="não pode ser nulo"):
        EarningUpdate(**{field: None})


def test_update_accepts_null_platform() -> None:
    assert EarningUpdate(platform=None).model_dump(exclude_unset=True) == {"platform": None}
