"""Database engine and per-request sessions.

NullPool on purpose: Neon's free compute scales to zero when idle, and pooled connections held
open by the app would keep it awake and burn the monthly compute allowance.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings

_engine: Engine | None = None
_factory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, _factory
    if _engine is None:
        url = get_settings().sqlalchemy_url
        if not url:
            raise RuntimeError("DATABASE_URL is not set.")
        _engine = create_engine(url, poolclass=NullPool, future=True)
        _factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def reset_engine() -> None:
    """Tests use this after changing DATABASE_URL."""
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None


def get_db() -> Iterator[Session]:
    get_engine()
    db = _factory()
    try:
        yield db
    finally:
        db.close()
