import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.integration


def test_rollback_after_integrity_error_keeps_session_usable(db_session: Session) -> None:
    repository = UserRepository(db_session)
    repository.save(User(name="John", email="john@example.com", password_hash="x"))

    with pytest.raises(IntegrityError):
        repository.save(User(name="Outro", email="john@example.com", password_hash="x"))
    repository.rollback()

    assert repository.get_by_email("john@example.com") is not None
