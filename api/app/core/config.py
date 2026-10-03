from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-local-development-only-secret"
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Expedientes API"
    environment: Literal["local", "test", "production"] = "local"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://pi_iv:pi_iv@localhost:5433/pi_iv"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440

    @model_validator(mode="after")
    def require_jwt_secret_in_production(self) -> Self:
        if self.environment != "production":
            return self
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set in production")
        if len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must have at least {MIN_JWT_SECRET_LENGTH} characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
