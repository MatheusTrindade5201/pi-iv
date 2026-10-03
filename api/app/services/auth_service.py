from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest

INVALID_CREDENTIALS = "E-mail ou senha inválidos"
EMAIL_TAKEN = "E-mail já cadastrado"

_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthService:
    def __init__(self, repository: UserRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def register(self, data: RegisterRequest) -> User:
        if self.repository.get_by_email(data.email) is not None:
            raise ConflictError(EMAIL_TAKEN)

        user = User(name=data.name, email=data.email, password_hash=hash_password(data.password))
        try:
            return self.repository.save(user)
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(EMAIL_TAKEN) from exc

    def authenticate(self, email: str, password: str) -> str:
        user = self.repository.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError(INVALID_CREDENTIALS)
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError(INVALID_CREDENTIALS)
        return create_access_token(user.id, self.settings)
