"""
@file tests/integration/migrations/test_perf_indexes_migration.py
@brief Round-trip (upgrade, downgrade, upgrade) of migration 0034_perf_indexes on real Postgres.

Runs in a scratch database so the shared test DB is never downgraded.
"""

import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command

ROOT = Path(__file__).resolve().parents[3]
BASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
PREV = "0033_branding_glass_defaults"
REV = "0034_perf_indexes"
ATTEND_IDX = "attendance_user_idx"
UNREAD_IDX = "notifications_user_unread_idx"
MEDIA_IDX = "post_media_media_idx"


@pytest.fixture
def scratch_db(monkeypatch):
    """@brief Create an empty scratch DB, point Settings at it, drop afterwards."""
    from app.core.config import get_settings

    name = f"nexara_mig_{uuid.uuid4().hex[:8]}"
    url = make_url(BASE_URL)
    admin = create_engine(url.set(drivername="postgresql+psycopg2"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    async_url = url.set(database=name).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", async_url)
    get_settings.cache_clear()
    engine = create_engine(url.set(drivername="postgresql+psycopg2", database=name))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
        get_settings.cache_clear()


def _cfg() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def _indexdef(engine, name: str) -> str | None:
    """@brief Return pg_indexes.indexdef for an index name, or None if absent."""
    with engine.connect() as c:
        return c.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :n"), {"n": name}
        ).scalar_one_or_none()


def test_upgrade_downgrade_upgrade_perf_indexes(scratch_db) -> None:
    cfg = _cfg()
    engine = scratch_db
    command.upgrade(cfg, PREV)
    assert _indexdef(engine, ATTEND_IDX) is None
    assert _indexdef(engine, MEDIA_IDX) is None
    old_unread = _indexdef(engine, UNREAD_IDX)
    assert old_unread is not None
    assert "created_at" not in old_unread

    command.upgrade(cfg, REV)
    attend = _indexdef(engine, ATTEND_IDX)
    assert attend is not None
    assert "(user_id)" in attend
    media = _indexdef(engine, MEDIA_IDX)
    assert media is not None
    assert "(media_id)" in media
    new_unread = _indexdef(engine, UNREAD_IDX)
    assert new_unread is not None
    assert "created_at DESC" in new_unread
    assert "read_at IS NULL" in new_unread
    assert "dismissed_at IS NULL" in new_unread

    command.downgrade(cfg, "-1")
    assert _indexdef(engine, ATTEND_IDX) is None
    assert _indexdef(engine, MEDIA_IDX) is None
    restored = _indexdef(engine, UNREAD_IDX)
    assert restored is not None
    assert "created_at" not in restored

    command.upgrade(cfg, REV)
    assert _indexdef(engine, ATTEND_IDX) is not None
    assert "created_at DESC" in (_indexdef(engine, UNREAD_IDX) or "")
