from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.shift import ShiftListQuery

pytestmark = pytest.mark.unit


def test_defaults() -> None:
    query = ShiftListQuery()

    assert (query.date_from, query.date_to) == (None, None)
    assert query.tz == "America/Sao_Paulo"
    assert (query.page, query.size) == (1, 20)


def test_accepts_aliases_from_and_to() -> None:
    query = ShiftListQuery.model_validate({"from": "2026-09-01", "to": "2026-09-30"})

    assert query.date_from == date(2026, 9, 1)
    assert query.date_to == date(2026, 9, 30)


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2026-09-30", "to": "2026-09-01"},
        {"tz": "Mars/Olympus"},
        {"tz": ""},
        {"page": 0},
        {"size": 0},
        {"size": 101},
    ],
)
def test_invalid_query_is_rejected(params: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ShiftListQuery.model_validate(params)
