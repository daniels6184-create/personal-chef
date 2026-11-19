"""Every test gets a freshly migrated Postgres database (the real migrations, not create_all).

Set TEST_DATABASE_URL to point somewhere else; it defaults to the local dev server on :5433.
The database named there is WIPED by every test.
"""
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@/chef_test?host=/tmp&port=5433")
PASSWORD = "correct horse battery staple"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ["DATABASE_URL"] = TEST_DB
os.environ["APP_PASSWORD"] = PASSWORD
os.environ["APP_ORIGIN"] = "http://testserver"
os.environ["COOKIE_SECURE"] = "false"
os.environ.setdefault("FRONTEND_DIR", "")

from app import db as appdb  # noqa: E402
from app.config import get_settings  # noqa: E402

CSRF = {"X-Requested-With": "personal-chef"}


def _fresh_schema():
    url = get_settings().sqlalchemy_url
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    eng.dispose()
    cfg = Config(os.path.join(HERE, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(HERE, "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture
def client():
    get_settings.cache_clear()
    appdb.reset_engine()
    _fresh_schema()
    from fastapi.testclient import TestClient

    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c
    appdb.reset_engine()


@pytest.fixture
def signed_in(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD}, headers=CSRF)
    assert r.status_code == 200, r.text
    return client
