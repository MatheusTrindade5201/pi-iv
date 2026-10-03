import pytest
from fastapi.testclient import TestClient

from app.models import User
from tests.conftest import USER_PASSWORD

pytestmark = pytest.mark.integration

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def register_payload(**overrides: str) -> dict[str, str]:
    data = {
        "name": "Maria Silva",
        "email": "maria@example.com",
        "password": "senha-segura-123",
        "password_confirm": "senha-segura-123",
    }
    return data | overrides


def test_register_creates_user(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json=register_payload(email="Maria@Example.com"))

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Maria Silva"
    assert body["email"] == "maria@example.com"
    assert set(body) == {"id", "name", "email", "created_at"}


@pytest.mark.parametrize("email", ["john@example.com", "JOHN@example.com"])
def test_register_rejects_existing_email(client: TestClient, user: User, email: str) -> None:
    response = client.post(REGISTER_URL, json=register_payload(email=email))

    assert response.status_code == 409
    assert response.json() == {"detail": "E-mail já cadastrado"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"password_confirm": "outra-senha-123"},
        {"password": "curta", "password_confirm": "curta"},
        {"email": "nao-e-email"},
        {"name": ""},
    ],
)
def test_register_validates_payload(client: TestClient, overrides: dict[str, str]) -> None:
    response = client.post(REGISTER_URL, json=register_payload(**overrides))

    assert response.status_code == 422


def test_login_returns_token_that_authenticates(client: TestClient, user: User) -> None:
    response = client.post(LOGIN_URL, json={"email": "John@Example.com", "password": USER_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)


@pytest.mark.parametrize(
    ("email", "password"),
    [("john@example.com", "senha-errada-123"), ("ninguem@example.com", USER_PASSWORD)],
)
def test_login_rejects_invalid_credentials(
    client: TestClient, user: User, email: str, password: str
) -> None:
    response = client.post(LOGIN_URL, json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json() == {"detail": "E-mail ou senha inválidos"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_register_then_login_flow(client: TestClient) -> None:
    client.post(REGISTER_URL, json=register_payload())

    response = client.post(
        LOGIN_URL, json={"email": "maria@example.com", "password": "senha-segura-123"}
    )

    assert response.status_code == 200
