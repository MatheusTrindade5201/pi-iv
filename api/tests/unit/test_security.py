import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_does_not_store_plain_text() -> None:
    password_hash = hash_password("senha-segura-123")

    assert password_hash != "senha-segura-123"
    assert password_hash.startswith("$argon2")


def test_verify_password_accepts_correct_password() -> None:
    assert verify_password("senha-segura-123", hash_password("senha-segura-123"))


def test_verify_password_rejects_wrong_password() -> None:
    assert not verify_password("outra-senha", hash_password("senha-segura-123"))


def test_access_token_roundtrip(settings: Settings) -> None:
    user_id = uuid.uuid4()

    assert decode_access_token(create_access_token(user_id, settings), settings) == user_id


def test_expired_token_is_rejected(settings: Settings) -> None:
    issued_at = datetime.now(UTC) - timedelta(minutes=settings.jwt_expires_minutes + 1)
    token = create_access_token(uuid.uuid4(), settings, now=issued_at)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_token_issued_slightly_in_the_future_is_accepted(settings: Settings) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, settings, now=datetime.now(UTC) + timedelta(seconds=5))

    assert decode_access_token(token, settings) == user_id


def test_token_issued_beyond_leeway_is_rejected(settings: Settings) -> None:
    issued_at = datetime.now(UTC) + timedelta(seconds=settings.jwt_leeway_seconds + 60)
    token = create_access_token(uuid.uuid4(), settings, now=issued_at)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_token_signed_with_other_secret_is_rejected(settings: Settings) -> None:
    other = settings.model_copy(update={"jwt_secret": "another-secret-with-at-least-32-chars"})
    token = create_access_token(uuid.uuid4(), other)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


def test_malformed_token_is_rejected(settings: Settings) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-jwt", settings)


@pytest.mark.parametrize(
    "payload",
    [
        {"exp": datetime.now(UTC) + timedelta(hours=1)},
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(hours=1)},
    ],
)
def test_token_without_valid_subject_is_rejected(settings: Settings, payload: dict) -> None:
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)
