import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, Shift, ShiftStatus, User, Vehicle
from tests.factories import (
    make_earning,
    make_finished_shift,
    make_fuel_price,
    make_shift,
    make_track_point,
    make_user,
    make_vehicle,
)

pytestmark = pytest.mark.integration

URL = "/api/v1/shifts"


@pytest.fixture
def vehicle(db_session: Session, user: User) -> Vehicle:
    make_fuel_price(db_session, user, fuel_id=GASOLINE_ID, price_per_liter=Decimal("6.200"))
    make_fuel_price(db_session, user, fuel_id=ETHANOL_ID, price_per_liter=Decimal("3.750"))
    return make_vehicle(db_session, user)


def start(client: TestClient, headers: dict[str, str], **body: object):
    payload = {key: str(value) for key, value in body.items()}
    return client.post(URL, json=payload, headers=headers)


def test_start_shift(client: TestClient, auth_headers: dict[str, str], vehicle: Vehicle) -> None:
    response = start(client, auth_headers, vehicle_id=vehicle.id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["vehicle_id"] == str(vehicle.id)
    assert body["fuel_id"] == str(GASOLINE_ID)
    assert body["price_per_liter_used"] == "6.200"
    assert body["kml_used"] == "32.00"
    assert body["ended_at"] is None
    assert body["summary"]["earnings_total"] == "0.00"
    assert body["gps"] == {"last_point_at": None, "gaps": []}


def test_flex_vehicle_requires_fuel(
    client: TestClient,
    auth_headers: dict[str, str],
    user: User,
    db_session: Session,
    vehicle: Vehicle,
) -> None:
    flex = make_vehicle(db_session, user, fuel_id=FLEX_ID)

    response = start(client, auth_headers, vehicle_id=flex.id)

    assert response.status_code == 422
    assert "Flex" in response.json()["detail"]


def test_flex_vehicle_uses_price_of_chosen_fuel(
    client: TestClient,
    auth_headers: dict[str, str],
    user: User,
    db_session: Session,
    vehicle: Vehicle,
) -> None:
    flex = make_vehicle(db_session, user, fuel_id=FLEX_ID)

    response = start(client, auth_headers, vehicle_id=flex.id, fuel_id=ETHANOL_ID)

    assert response.status_code == 201
    assert response.json()["fuel_id"] == str(ETHANOL_ID)
    assert response.json()["price_per_liter_used"] == "3.750"


def test_start_without_fuel_price_is_rejected(
    client: TestClient, auth_headers: dict[str, str], user: User, db_session: Session
) -> None:
    vehicle = make_vehicle(db_session, user)

    response = start(client, auth_headers, vehicle_id=vehicle.id)

    assert response.status_code == 409
    assert response.json() == {"detail": "Cadastre o preço do combustível antes de iniciar"}


def test_second_shift_in_progress_is_rejected(
    client: TestClient, auth_headers: dict[str, str], vehicle: Vehicle
) -> None:
    start(client, auth_headers, vehicle_id=vehicle.id)

    response = start(client, auth_headers, vehicle_id=vehicle.id)

    assert response.status_code == 409
    assert response.json() == {"detail": "Já existe um expediente em andamento"}


def test_start_with_vehicle_of_other_user_returns_404(
    client: TestClient, auth_headers: dict[str, str], db_session: Session, vehicle: Vehicle
) -> None:
    other_vehicle = make_vehicle(db_session, make_user(db_session))

    response = start(client, auth_headers, vehicle_id=other_vehicle.id)

    assert response.status_code == 404


def test_current_without_shift_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{URL}/current", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Nenhum expediente em andamento"}


def test_current_returns_partial_summary_and_gps_status(
    client: TestClient,
    auth_headers: dict[str, str],
    user: User,
    db_session: Session,
    vehicle: Vehicle,
) -> None:
    started_at = datetime.now(UTC) - timedelta(hours=2)
    shift = make_shift(
        db_session, user, vehicle, started_at=started_at, price_per_liter_used=Decimal("6.200")
    )
    make_earning(db_session, shift, amount=Decimal("20.00"))
    make_earning(db_session, shift, amount=Decimal("30.00"))
    make_track_point(db_session, shift, recorded_at=started_at + timedelta(minutes=5))
    make_track_point(db_session, shift, recorded_at=started_at + timedelta(minutes=15))

    response = client.get(f"{URL}/current", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(shift.id)
    assert body["summary"]["earnings_total"] == "50.00"
    assert body["summary"]["idle_minutes"] == 10
    assert body["summary"]["fuel_cost"] == "0.15"
    assert body["summary"]["profit"] == "49.85"
    assert body["summary"]["distance_km"] == "0.000"
    assert body["summary"]["profit_per_km"] is None
    assert body["summary"]["duration_minutes"] >= 120
    assert [gap["minutes"] for gap in body["gps"]["gaps"]] == [5, 10]
    assert body["gps"]["last_point_at"] is not None


def test_finish_persists_metrics(
    client: TestClient, auth_headers: dict[str, str], vehicle: Vehicle, db_session: Session
) -> None:
    shift_id = start(client, auth_headers, vehicle_id=vehicle.id).json()["id"]
    make_earning(db_session, db_session.get(Shift, uuid.UUID(shift_id)), amount=Decimal("80.00"))

    response = client.post(f"{URL}/{shift_id}/finish", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "finished"
    assert body["ended_at"] is not None
    assert body["summary"]["earnings_total"] == "80.00"
    stored = db_session.get(Shift, uuid.UUID(shift_id))
    db_session.refresh(stored)
    assert stored.status == ShiftStatus.FINISHED
    assert stored.earnings_total == Decimal("80.00")
    assert stored.profit == Decimal("80.00")
    assert stored.fuel_cost == Decimal("0.00")
    assert stored.duration_minutes == 0


def test_finished_shift_lifecycle(
    client: TestClient, auth_headers: dict[str, str], vehicle: Vehicle
) -> None:
    shift_id = start(client, auth_headers, vehicle_id=vehicle.id).json()["id"]
    client.post(f"{URL}/{shift_id}/finish", headers=auth_headers)

    again = client.post(f"{URL}/{shift_id}/finish", headers=auth_headers)
    current = client.get(f"{URL}/current", headers=auth_headers)
    detail = client.get(f"{URL}/{shift_id}", headers=auth_headers)
    new_shift = start(client, auth_headers, vehicle_id=vehicle.id)

    assert again.status_code == 409
    assert again.json() == {"detail": "Expediente já encerrado"}
    assert current.status_code == 404
    assert detail.status_code == 200
    assert detail.json()["status"] == "finished"
    assert new_shift.status_code == 201


@pytest.mark.parametrize("path", ["", "/finish"])
def test_shift_of_other_user_returns_404(
    client: TestClient, auth_headers: dict[str, str], db_session: Session, path: str
) -> None:
    other = make_user(db_session)
    shift = make_shift(db_session, other, make_vehicle(db_session, other))

    method = "post" if path else "get"
    response = client.request(method, f"{URL}/{shift.id}{path}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Expediente não encontrado"}


def test_list_paginates_in_descending_order(
    client: TestClient,
    auth_headers: dict[str, str],
    user: User,
    db_session: Session,
    vehicle: Vehicle,
) -> None:
    base = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    shifts = [
        make_finished_shift(db_session, user, vehicle, started_at=base + timedelta(days=day))
        for day in range(3)
    ]
    other = make_user(db_session)
    make_finished_shift(db_session, other, make_vehicle(db_session, other), started_at=base)

    first = client.get(URL, params={"page": 1, "size": 2}, headers=auth_headers).json()
    second = client.get(URL, params={"page": 2, "size": 2}, headers=auth_headers).json()

    assert first["total"] == 3
    assert (first["page"], first["size"]) == (1, 2)
    assert [item["id"] for item in first["items"]] == [str(shifts[2].id), str(shifts[1].id)]
    assert [item["id"] for item in second["items"]] == [str(shifts[0].id)]
    assert first["items"][0]["summary"]["profit"] == "187.40"
    assert "gps" not in first["items"][0]


def test_list_filters_by_local_date(
    client: TestClient,
    auth_headers: dict[str, str],
    user: User,
    db_session: Session,
    vehicle: Vehicle,
) -> None:
    late_night = datetime(2026, 9, 20, 2, 30, tzinfo=UTC)
    shift = make_finished_shift(db_session, user, vehicle, started_at=late_night)

    on_local_day = client.get(
        URL, params={"from": "2026-09-19", "to": "2026-09-19"}, headers=auth_headers
    ).json()
    on_utc_day = client.get(
        URL, params={"from": "2026-09-20", "to": "2026-09-20"}, headers=auth_headers
    ).json()
    in_utc = client.get(
        URL, params={"from": "2026-09-20", "to": "2026-09-20", "tz": "UTC"}, headers=auth_headers
    ).json()

    assert [item["id"] for item in on_local_day["items"]] == [str(shift.id)]
    assert on_utc_day["items"] == []
    assert [item["id"] for item in in_utc["items"]] == [str(shift.id)]


def test_list_shows_in_progress_without_summary(
    client: TestClient, auth_headers: dict[str, str], vehicle: Vehicle
) -> None:
    start(client, auth_headers, vehicle_id=vehicle.id)

    items = client.get(URL, headers=auth_headers).json()["items"]

    assert items[0]["status"] == "in_progress"
    assert items[0]["summary"] is None


@pytest.mark.parametrize(
    "params", [{"from": "2026-09-30", "to": "2026-09-01"}, {"tz": "Nope/Zone"}]
)
def test_list_rejects_invalid_query(
    client: TestClient, auth_headers: dict[str, str], params: dict[str, str]
) -> None:
    assert client.get(URL, params=params, headers=auth_headers).status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", ""),
        ("get", ""),
        ("get", "/current"),
        ("get", f"/{uuid.uuid4()}"),
        ("post", f"/{uuid.uuid4()}/finish"),
    ],
)
def test_shifts_require_authentication(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, f"{URL}{path}").status_code == 401
