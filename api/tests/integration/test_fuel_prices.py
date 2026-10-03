import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ETHANOL_ID, FLEX_ID, GASOLINE_ID, FuelPrice, User
from tests.factories import make_fuel_price, make_user

pytestmark = pytest.mark.integration

CURRENT_URL = "/api/v1/fuel-prices/current"
UPDATE_URL = "/api/v1/fuel-prices"


def prices_payload(*items: tuple[uuid.UUID, str]) -> dict:
    return {
        "prices": [{"fuel_id": str(fuel_id), "price_per_liter": price} for fuel_id, price in items]
    }


def as_map(body: list[dict]) -> dict[str, Decimal]:
    return {item["fuel_name"]: Decimal(item["price_per_liter"]) for item in body}


def test_new_user_has_no_prices(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(CURRENT_URL, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_update_prices_and_read_current(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.put(
        UPDATE_URL,
        json=prices_payload((GASOLINE_ID, "6.20"), (ETHANOL_ID, "3.75")),
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert as_map(response.json()) == {"Gasolina": Decimal("6.20"), "Etanol": Decimal("3.75")}
    assert set(response.json()[0]) == {"fuel_id", "fuel_name", "price_per_liter", "valid_from"}

    current = client.get(CURRENT_URL, headers=auth_headers)
    assert as_map(current.json()) == as_map(response.json())


def test_partial_update_keeps_other_prices_and_history(
    client: TestClient, auth_headers: dict[str, str], user: User, db_session: Session
) -> None:
    client.put(
        UPDATE_URL,
        json=prices_payload((GASOLINE_ID, "6.20"), (ETHANOL_ID, "3.75")),
        headers=auth_headers,
    )

    response = client.put(
        UPDATE_URL, json=prices_payload((GASOLINE_ID, "6.49")), headers=auth_headers
    )

    assert response.status_code == 200
    assert as_map(response.json()) == {"Gasolina": Decimal("6.49"), "Etanol": Decimal("3.75")}
    gasoline_history = db_session.scalar(
        select(func.count())
        .select_from(FuelPrice)
        .where(FuelPrice.user_id == user.id, FuelPrice.fuel_id == GASOLINE_ID)
    )
    assert gasoline_history == 2


def test_prices_of_other_users_are_not_visible(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    make_fuel_price(db_session, make_user(db_session), price_per_liter=Decimal("9.99"))

    response = client.get(CURRENT_URL, headers=auth_headers)

    assert response.json() == []


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            prices_payload((FLEX_ID, "5.00")),
            "Flex não tem preço próprio; informe Gasolina ou Etanol",
        ),
        (prices_payload((uuid.uuid4(), "5.00")), "Combustível não encontrado"),
    ],
)
def test_update_rejects_invalid_fuel(
    client: TestClient, auth_headers: dict[str, str], payload: dict, detail: str
) -> None:
    response = client.put(UPDATE_URL, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize(
    "payload",
    [
        {"prices": []},
        prices_payload((GASOLINE_ID, "0")),
        prices_payload((GASOLINE_ID, "6.20"), (GASOLINE_ID, "6.30")),
    ],
)
def test_update_validates_body(
    client: TestClient, auth_headers: dict[str, str], payload: dict
) -> None:
    assert client.put(UPDATE_URL, json=payload, headers=auth_headers).status_code == 422


@pytest.mark.parametrize(("method", "url"), [("get", CURRENT_URL), ("put", UPDATE_URL)])
def test_fuel_prices_require_authentication(client: TestClient, method: str, url: str) -> None:
    response = client.request(method, url, json=prices_payload((GASOLINE_ID, "6.20")))

    assert response.status_code == 401
