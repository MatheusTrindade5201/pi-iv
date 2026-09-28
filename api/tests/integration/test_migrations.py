from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, make_url, select, text
from sqlalchemy.orm import Session

from app.models import Fuel
from app.models.fuel import SEED_FUELS
from tests.alembic_utils import make_alembic_config

pytestmark = pytest.mark.integration


@pytest.fixture
def fresh_database_url(engine: Engine, postgres_url: str) -> Iterator[str]:
    name = "migrations_roundtrip"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
        conn.execute(text(f"CREATE DATABASE {name}"))

    yield make_url(postgres_url).set(database=name).render_as_string(hide_password=False)

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))


def test_seed_creates_fuels_with_fixed_ids(db_session: Session) -> None:
    fuels = db_session.scalars(select(Fuel)).all()

    assert {fuel.id: fuel.name for fuel in fuels} == SEED_FUELS


def test_models_and_migrations_are_in_sync(postgres_url: str) -> None:
    command.check(make_alembic_config(postgres_url))


def test_downgrade_and_upgrade_roundtrip(fresh_database_url: str) -> None:
    config = make_alembic_config(fresh_database_url)
    engine = create_engine(fresh_database_url)

    try:
        command.upgrade(config, "head")
        assert "shifts" in inspect(engine).get_table_names()

        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
        with engine.connect() as conn:
            enum_count = conn.scalar(
                text("SELECT count(*) FROM pg_type WHERE typname = 'shift_status'")
            )
        assert enum_count == 0

        command.upgrade(config, "head")
        assert "track_points" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
