import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, User
from tests.factories import make_shift, make_user, make_vehicle

pytestmark = pytest.mark.integration

URL = "/api/v1/vehicles"
CREATED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def vehicle_payload(**overrides: object) -> dict[str, object]:
    data = {
        "model": "Honda CG 160",
        "fuel_id": str(GASOLINE_ID),
        "declared_kml": "32",
        "displacement_cc": 160,
        "year": 2022,
    }
    return data | overrides


def create(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post(URL, json=vehicle_payload(**overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_create_vehicle(client: TestClient, auth_headers: dict[str, str]) -> None:
    body = create(client, auth_headers)

    assert body["model"] == "Honda CG 160"
    assert body["fuel_id"] == str(GASOLINE_ID)
    assert body["fuel_name"] == "Gasolina"
    assert body["declared_kml"] == "32.00"
    assert body["displacement_cc"] == 160
    assert body["year"] == 2022
    assert set(body) == {
        "id",
        "model",
        "fuel_id",
        "fuel_name",
        "declared_kml",
        "displacement_cc",
        "year",
        "created_at",
    }


def test_create_flex_vehicle_without_optional_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    body = create(client, auth_headers, fuel_id=str(FLEX_ID), displacement_cc=None, year=None)

    assert body["fuel_name"] == "Flex"
    assert body["displacement_cc"] is None
    assert body["year"] is None


def test_list_returns_only_own_vehicles_in_creation_order(
    client: TestClient, auth_headers: dict[str, str], user: User, db_session: Session
) -> None:
    make_vehicle(db_session, make_user(db_session), model="Moto de outro")
    second = make_vehicle(
        db_session, user, model="Segunda", created_at=CREATED_AT + timedelta(days=1)
    )
    first = make_vehicle(db_session, user, model="Primeira", created_at=CREATED_AT)

    response = client.get(URL, headers=auth_headers)

    assert response.status_code == 200
    assert [vehicle["id"] for vehicle in response.json()] == [str(first.id), str(second.id)]


def test_get_vehicle(client: TestClient, auth_headers: dict[str, str]) -> None:
    vehicle = create(client, auth_headers)

    response = client.get(f"{URL}/{vehicle['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == vehicle


def test_partial_update(client: TestClient, auth_headers: dict[str, str]) -> None:
    vehicle = create(client, auth_headers)

    response = client.patch(
        f"{URL}/{vehicle['id']}", json={"declared_kml": "30.5"}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["declared_kml"] == "30.50"
    assert body["model"] == vehicle["model"]
    assert body["year"] == vehicle["year"]


def test_update_fuel_and_clear_year(client: TestClient, auth_headers: dict[str, str]) -> None:
    vehicle = create(client, auth_headers)

    response = client.patch(
        f"{URL}/{vehicle['id']}",
        json={"fuel_id": str(ETHANOL_ID), "year": None},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["fuel_name"] == "Etanol"
    assert response.json()["year"] is None
    assert client.get(f"{URL}/{vehicle['id']}", headers=auth_headers).json()["year"] is None


def test_delete_vehicle(client: TestClient, auth_headers: dict[str, str]) -> None:
    vehicle = create(client, auth_headers)

    response = client.delete(f"{URL}/{vehicle['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(f"{URL}/{vehicle['id']}", headers=auth_headers).status_code == 404


def test_delete_vehicle_with_shifts_is_rejected(
    client: TestClient, auth_headers: dict[str, str], user: User, db_session: Session
) -> None:
    vehicle = make_vehicle(db_session, user)
    make_shift(db_session, user, vehicle)

    response = client.delete(f"{URL}/{vehicle.id}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Veículo possui expedientes registrados"}


@pytest.mark.parametrize(
    ("method", "body"), [("get", None), ("patch", {"model": "Hack"}), ("delete", None)]
)
def test_vehicle_of_other_user_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    method: str,
    body: dict | None,
) -> None:
    other_vehicle = make_vehicle(db_session, make_user(db_session))

    response = client.request(method, f"{URL}/{other_vehicle.id}", json=body, headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Veículo não encontrado"}


def test_unknown_vehicle_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(f"{URL}/{uuid.uuid4()}", headers=auth_headers).status_code == 404


def test_unknown_fuel_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        URL, json=vehicle_payload(fuel_id=str(uuid.uuid4())), headers=auth_headers
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Combustível não encontrado"}


@pytest.mark.parametrize(
    "overrides",
    [{"model": ""}, {"declared_kml": "0"}, {"year": 1900}, {"displacement_cc": 0}],
)
def test_invalid_payload_is_rejected(
    client: TestClient, auth_headers: dict[str, str], overrides: dict[str, object]
) -> None:
    response = client.post(URL, json=vehicle_payload(**overrides), headers=auth_headers)

    assert response.status_code == 422


def test_update_rejects_null_on_required_field(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    vehicle = create(client, auth_headers)

    response = client.patch(f"{URL}/{vehicle['id']}", json={"model": None}, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", ""),
        ("get", ""),
        ("get", f"/{uuid.uuid4()}"),
        ("patch", f"/{uuid.uuid4()}"),
        ("delete", f"/{uuid.uuid4()}"),
    ],
)
def test_vehicles_require_authentication(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, f"{URL}{path}", json=vehicle_payload())

    assert response.status_code == 401
