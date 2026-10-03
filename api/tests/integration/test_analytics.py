from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Vehicle
from app.services.date_range import local_today
from tests.factories import make_finished_shift, make_shift, make_user, make_vehicle

pytestmark = pytest.mark.integration

DAILY_URL = "/api/v1/analytics/daily"
SUMMARY_URL = "/api/v1/analytics/summary"
SEPTEMBER = {"from": "2026-09-01", "to": "2026-09-30"}


@pytest.fixture
def vehicle(db_session: Session, user: User) -> Vehicle:
    return make_vehicle(db_session, user)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=UTC)


def test_daily_groups_by_local_day_newest_first(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=at(17, 12))
    make_finished_shift(
        db_session,
        user,
        vehicle,
        started_at=at(18, 11),
        earnings_total=Decimal("100.00"),
        fuel_cost=Decimal("20.00"),
        profit=Decimal("80.00"),
        distance_km=Decimal("30.000"),
        duration_minutes=120,
        idle_minutes=10,
    )
    make_finished_shift(db_session, user, vehicle, started_at=at(18, 18))

    response = client.get(DAILY_URL, params=SEPTEMBER, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert [day["date"] for day in body] == ["2026-09-18", "2026-09-17"]
    assert body[0] == {
        "date": "2026-09-18",
        "shifts_count": 2,
        "earnings_total": "345.00",
        "fuel_cost": "77.60",
        "profit": "267.40",
        "distance_km": "108.200",
        "duration_minutes": 360,
        "idle_minutes": 40,
    }
    assert body[1]["profit"] == "187.40"


def test_late_night_shift_counts_on_local_day(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=at(20, 2, 30))

    local = client.get(DAILY_URL, params=SEPTEMBER, headers=auth_headers).json()
    utc = client.get(DAILY_URL, params=SEPTEMBER | {"tz": "UTC"}, headers=auth_headers).json()

    assert [day["date"] for day in local] == ["2026-09-19"]
    assert [day["date"] for day in utc] == ["2026-09-20"]


def test_only_finished_shifts_of_user_in_range_are_counted(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=at(10, 12))
    make_finished_shift(db_session, user, vehicle, started_at=datetime(2026, 8, 31, 12, tzinfo=UTC))
    make_shift(db_session, user, vehicle, started_at=at(11, 12))
    other = make_user(db_session)
    make_finished_shift(db_session, other, make_vehicle(db_session, other), started_at=at(10, 12))

    body = client.get(DAILY_URL, params=SEPTEMBER, headers=auth_headers).json()

    assert [(day["date"], day["shifts_count"]) for day in body] == [("2026-09-10", 1)]


def test_summary_totals_and_rates(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=at(15, 12))
    make_finished_shift(db_session, user, vehicle, started_at=at(16, 12))

    response = client.get(SUMMARY_URL, params=SEPTEMBER, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "from": "2026-09-01",
        "to": "2026-09-30",
        "days_worked": 2,
        "shifts_count": 2,
        "earnings_total": "490.00",
        "fuel_cost": "115.20",
        "profit": "374.80",
        "distance_km": "156.400",
        "duration_minutes": 480,
        "idle_minutes": 60,
        "profit_per_hour": "46.85",
        "profit_per_km": "2.40",
        "avg_profit_per_day": "187.40",
    }


def test_two_shifts_same_day_count_as_one_day_worked(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=at(15, 11))
    make_finished_shift(db_session, user, vehicle, started_at=at(15, 18))

    body = client.get(SUMMARY_URL, params=SEPTEMBER, headers=auth_headers).json()

    assert (body["days_worked"], body["shifts_count"]) == (1, 2)
    assert body["avg_profit_per_day"] == "374.80"


def test_empty_period(client: TestClient, auth_headers: dict[str, str]) -> None:
    daily = client.get(DAILY_URL, params=SEPTEMBER, headers=auth_headers).json()
    summary = client.get(SUMMARY_URL, params=SEPTEMBER, headers=auth_headers).json()

    assert daily == []
    assert summary["shifts_count"] == 0
    assert summary["days_worked"] == 0
    assert Decimal(summary["profit"]) == 0
    assert summary["profit_per_hour"] is None
    assert summary["profit_per_km"] is None
    assert summary["avg_profit_per_day"] is None


def test_default_period_is_last_30_days(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    user: User,
    vehicle: Vehicle,
) -> None:
    make_finished_shift(db_session, user, vehicle, started_at=datetime.now(UTC) - timedelta(days=2))
    make_finished_shift(
        db_session, user, vehicle, started_at=datetime.now(UTC) - timedelta(days=40)
    )

    summary = client.get(SUMMARY_URL, headers=auth_headers).json()
    daily = client.get(DAILY_URL, headers=auth_headers).json()

    today = local_today("America/Sao_Paulo")
    assert summary["to"] == today.isoformat()
    assert summary["from"] == (today - timedelta(days=29)).isoformat()
    assert summary["shifts_count"] == 1
    assert len(daily) == 1


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2026-09-30", "to": "2026-09-01"},
        {"from": "2024-01-01", "to": "2026-01-01"},
        {"tz": "X/Y"},
    ],
)
@pytest.mark.parametrize("path", [DAILY_URL, SUMMARY_URL])
def test_invalid_params(
    client: TestClient, auth_headers: dict[str, str], path: str, params: dict[str, str]
) -> None:
    assert client.get(path, params=params, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("path", [DAILY_URL, SUMMARY_URL])
def test_analytics_require_authentication(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401
