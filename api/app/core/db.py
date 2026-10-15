from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(url: str) -> Engine:
    # Sem prepared statements: o pooler do Supabase em modo transaction não os suporta.
    return create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
