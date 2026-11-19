"""Alembic runs with the app's own DATABASE_URL handling (adds sslmode for Neon)."""
from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models import Base

target_metadata = Base.metadata


def run() -> None:
    engine = create_engine(get_settings().sqlalchemy_url, poolclass=NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run()
