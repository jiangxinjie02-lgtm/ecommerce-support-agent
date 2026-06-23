from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "ecommerce.db"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_database_url: str | None = None


def get_database_url() -> str:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        return configured
    DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


def configure_database(database_url: str | None = None) -> Engine:
    global _engine, _session_factory, _database_url

    url = database_url or get_database_url()
    if _engine is not None and _database_url == url:
        return _engine

    if _engine is not None:
        _engine.dispose()

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _session_factory = sessionmaker(
        bind=_engine,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    _database_url = url
    return _engine


def init_database(drop_existing: bool = False) -> Engine:
    engine = configure_database()
    if drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope() -> Iterator[Session]:
    if _session_factory is None:
        init_database()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_health() -> dict[str, str]:
    engine = configure_database()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "dialect": engine.dialect.name}
