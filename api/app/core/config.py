from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Expedientes API"
    environment: Literal["local", "test", "production"] = "local"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://pi_iv:pi_iv@localhost:5433/pi_iv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
