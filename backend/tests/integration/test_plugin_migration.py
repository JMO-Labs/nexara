"""
@file test_plugin_migration.py
@brief Run alembic upgrade head / downgrade base on a scratch database.
"""

import os
import uuid
from pathlib import Path

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import get_settings

BACKEND = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)


@pytest.fixture
def scratch_db(monkeypatch):
    """@brief Create a throwaway database and point settings at it."""
    url = make_url(BASE_URL)
    name = f"mig_{uuid.uuid4().hex[:10]}"

    def admin():
        c = psycopg2.connect(
            host=url.host, port=url.port, user=url.username,
            password=url.password, dbname="postgres",
        )  # fmt: skip
        c.autocommit = True
        return c

    conn = admin()
    conn.cursor().execute(f'CREATE DATABASE "{name}"')
    conn.close()
    monkeypatch.setenv("DATABASE_URL", url.set(database=name).render_as_string(hide_password=False))
    get_settings.cache_clear()
    yield name
    get_settings.cache_clear()
    conn = admin()
    conn.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    conn.close()


def test_upgrade_head_then_downgrade_base(scratch_db):
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "a78f91338679")  # drops plugin tables
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
