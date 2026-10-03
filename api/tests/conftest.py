from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from app.core.config import Settings
from app.core.db import create_db_engine, get_db
from app.core.security import create_access_token
from app.main import create_app
from app.models import User
from tests.alembic_utils import make_alembic_config
from tests.factories import make_user

USER_PASSWORD = "senha-segura-123"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None, environment="test", jwt_secret="test-secret-with-at-least-32-characters"
    )


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        command.upgrade(make_alembic_config(url), "head")
        yield url


@pytest.fixture(scope="session")
def engine(postgres_url: str) -> Iterator[Engine]:
    engine = create_db_engine(postgres_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(settings: Settings, db_session: Session) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user(db_session: Session) -> User:
    return make_user(db_session, password=USER_PASSWORD, email="john@example.com")


@pytest.fixture
def auth_headers(user: User, settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}
