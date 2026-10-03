import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import decode_access_token, verify_password
from app.models import User
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService

pytestmark = pytest.mark.unit

PASSWORD = "senha-segura-123"


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.fail_on_save = False
        self.rolled_back = False

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    def save(self, user: User) -> User:
        if self.fail_on_save:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))
        user.id = user.id or uuid.uuid4()
        user.created_at = user.created_at or datetime.now(UTC)
        self.users[user.id] = user
        return user

    def rollback(self) -> None:
        self.rolled_back = True


@pytest.fixture
def repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def service(repository: FakeUserRepository, settings: Settings) -> AuthService:
    return AuthService(repository, settings)


def register_request(email: str = "john@example.com") -> RegisterRequest:
    return RegisterRequest(
        name="John Doe", email=email, password=PASSWORD, password_confirm=PASSWORD
    )


def test_register_stores_hashed_password(service: AuthService) -> None:
    user = service.register(register_request())

    assert user.email == "john@example.com"
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


def test_register_rejects_existing_email(service: AuthService) -> None:
    service.register(register_request())

    with pytest.raises(ConflictError):
        service.register(register_request())


def test_register_translates_integrity_error_into_conflict(
    service: AuthService, repository: FakeUserRepository
) -> None:
    repository.fail_on_save = True

    with pytest.raises(ConflictError):
        service.register(register_request())
    assert repository.rolled_back


def test_authenticate_returns_token_for_user(service: AuthService, settings: Settings) -> None:
    user = service.register(register_request())

    token = service.authenticate("john@example.com", PASSWORD)

    assert decode_access_token(token, settings) == user.id


@pytest.mark.parametrize(
    ("email", "password"),
    [("john@example.com", "senha-errada-123"), ("ninguem@example.com", PASSWORD)],
)
def test_authenticate_rejects_invalid_credentials(
    service: AuthService, email: str, password: str
) -> None:
    service.register(register_request())

    with pytest.raises(UnauthorizedError, match="E-mail ou senha inválidos"):
        service.authenticate(email, password)
