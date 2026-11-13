"""
@file test_webhook_subscriptions_migration.py
@brief Migration d4e5f6a7b8c9: webhook_subscriptions table and partial indexes.
"""

import os
import uuid
from pathlib import Path

import psycopg2
import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.engine import make_url

from alembic import command
from app.core.config import get_settings

BACKEND = Path(__file__).resolve().parents[3]
BASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
REV = "d4e5f6a7b8c9"
PREV = "b2c3d4e5f6a7"


def _admin(url):
    c = psycopg2.connect(
        host=url.host, port=url.port, user=url.username,
        password=url.password, dbname="postgres",
    )  # fmt: skip
    c.autocommit = True
    return c


@pytest.fixture
def scratch(monkeypatch):
    """@brief Throwaway DB; yields (alembic config, sync engine)."""
    url = make_url(BASE_URL)
    name = f"mig_{uuid.uuid4().hex[:10]}"
    conn = _admin(url)
    conn.cursor().execute(f'CREATE DATABASE "{name}"')
    conn.close()
    monkeypatch.setenv("DATABASE_URL", url.set(database=name).render_as_string(hide_password=False))
    get_settings.cache_clear()
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    engine = sa.create_engine(url.set(drivername="postgresql+psycopg2", database=name))
    yield cfg, engine
    engine.dispose()
    get_settings.cache_clear()
    conn = _admin(url)
    conn.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    conn.close()


def test_upgrade_creates_table_and_indexes_and_downgrades(scratch):
    cfg, engine = scratch
    command.upgrade(cfg, PREV)
    command.upgrade(cfg, REV)
    with engine.begin() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'webhook_subscriptions'"
                )
            )
        }
        assert {
            "id", "community_id", "user_id", "url", "secret", "type_keys",
            "enabled", "failure_count", "last_failure_at", "created_at",
        } == cols  # fmt: skip
        idx = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT indexname FROM pg_indexes WHERE tablename = 'webhook_subscriptions'"
                )
            )
        }
        assert {"webhook_subs_community_idx", "webhook_subs_user_idx"} <= idx
    command.downgrade(cfg, PREV)
    with engine.begin() as conn:
        assert not conn.execute(
            sa.text("SELECT to_regclass('public.webhook_subscriptions')")
        ).scalar_one()
