import pytest

from app.core.config import Settings, get_settings

pytestmark = pytest.mark.unit


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.api_prefix == "/api/v1"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expires_minutes == 1440


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/app")
    monkeypatch.setenv("JWT_SECRET", "segredo-de-producao-com-mais-de-32-caracteres")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/app"
    assert settings.jwt_secret == "segredo-de-producao-com-mais-de-32-caracteres"


def test_production_requires_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        Settings(_env_file=None)


def test_production_rejects_short_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "curto")

    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(_env_file=None)


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
