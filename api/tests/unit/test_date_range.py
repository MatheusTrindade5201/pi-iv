from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.analytics import AnalyticsQuery
from app.services.date_range import local_range_to_utc, local_today

pytestmark = pytest.mark.unit


def test_local_range_in_sao_paulo() -> None:
    start, end = local_range_to_utc(date(2026, 9, 19), date(2026, 9, 20), "America/Sao_Paulo")

    assert start == datetime(2026, 9, 19, 3, 0, tzinfo=UTC)
    assert end == datetime(2026, 9, 21, 3, 0, tzinfo=UTC)


def test_local_range_in_utc_with_open_start() -> None:
    assert local_range_to_utc(None, date(2026, 9, 20), "UTC") == (
        None,
        datetime(2026, 9, 21, tzinfo=UTC),
    )


def test_local_today_uses_timezone() -> None:
    late_utc = datetime(2026, 9, 20, 2, 0, tzinfo=UTC)

    assert local_today("America/Sao_Paulo", late_utc) == date(2026, 9, 19)
    assert local_today("UTC", late_utc) == date(2026, 9, 20)


def test_analytics_query_defaults_to_last_30_days() -> None:
    query = AnalyticsQuery()

    assert query.date_to == local_today("America/Sao_Paulo")
    assert query.date_from == query.date_to - timedelta(days=29)


def test_analytics_query_fills_only_missing_from() -> None:
    query = AnalyticsQuery.model_validate({"to": "2026-09-30"})

    assert query.date_from == date(2026, 9, 1)


def test_analytics_query_accepts_366_days() -> None:
    query = AnalyticsQuery.model_validate({"from": "2025-01-01", "to": "2026-01-01"})

    assert (query.date_to - query.date_from).days == 365


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2025-01-01", "to": "2026-01-02"},
        {"from": "2026-09-30", "to": "2026-09-01"},
        {"from": "2099-01-01"},
        {"tz": "Nowhere/Land"},
    ],
)
def test_invalid_analytics_query(params: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        AnalyticsQuery.model_validate(params)
