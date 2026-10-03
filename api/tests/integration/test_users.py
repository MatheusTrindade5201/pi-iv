import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token
from app.models import User

pytestmark = pytest.mark.integration

ME_URL = "/api/v1/users/me"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_me_returns_current_user(
    client: TestClient, user: User, auth_headers: dict[str, str]
) -> None:
    response = client.get(ME_URL, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "created_at": response.json()["created_at"],
    }


def test_get_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_me_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(ME_URL, headers=bearer("not-a-jwt"))

    assert response.status_code == 401


def test_get_me_with_expired_token_returns_401(
    client: TestClient, user: User, settings: Settings
) -> None:
    issued_at = datetime.now(UTC) - timedelta(minutes=settings.jwt_expires_minutes + 1)
    token = create_access_token(user.id, settings, now=issued_at)

    response = client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401


def test_get_me_with_token_of_unknown_user_returns_401(
    client: TestClient, settings: Settings
) -> None:
    response = client.get(ME_URL, headers=bearer(create_access_token(uuid.uuid4(), settings)))

    assert response.status_code == 401


def test_update_me_changes_name(
    client: TestClient, user: User, auth_headers: dict[str, str], db_session: Session
) -> None:
    response = client.patch(ME_URL, json={"name": "  John Updated  "}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "John Updated"
    db_session.refresh(user)
    assert user.name == "John Updated"


def test_update_me_rejects_blank_name(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(ME_URL, json={"name": "   "}, headers=auth_headers)

    assert response.status_code == 422


def test_update_me_requires_authentication(client: TestClient) -> None:
    response = client.patch(ME_URL, json={"name": "Someone"})

    assert response.status_code == 401
