import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserUpdate

pytestmark = pytest.mark.unit


def register_data(**overrides: str) -> dict[str, str]:
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "senha-segura-123",
        "password_confirm": "senha-segura-123",
    }
    return data | overrides


def test_valid_register_request() -> None:
    request = RegisterRequest(**register_data(name="  John Doe  ", email="John@Example.COM"))

    assert request.name == "John Doe"
    assert request.email == "john@example.com"


def test_login_request_normalizes_email() -> None:
    assert LoginRequest(email="John@Example.com", password="x").email == "john@example.com"


@pytest.mark.parametrize(
    "overrides",
    [
        {"password_confirm": "outra-senha-123"},
        {"password": "curta", "password_confirm": "curta"},
        {"email": "nao-e-email"},
        {"name": "   "},
        {"name": "x" * 121},
    ],
)
def test_invalid_register_request(overrides: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**register_data(**overrides))


def test_user_update_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        UserUpdate(name="  ")
