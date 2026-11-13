"""
@file test_user_exports_migration.py
@brief Migration 0026_user_exports_table: schema, defaults and indexes on real Postgres.

Runs in a scratch database so the shared test DB is never touched.
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
REV = "0026_user_exports_table"


def _admin(url):
    c = psycopg2.connect(
        host=url.host, port=url.port, user=url.username,
        password=url.password, dbname="postgres",
    )  # fmt: skip
    c.autocommit = True
    return c


@pytest.fixture
def engine(monkeypatch):
    """@brief Scratch DB upgraded to REV; yields a sync engine."""
    url = make_url(BASE_URL)
    name = f"mig_{uuid.uuid4().hex[:10]}"
    conn = _admin(url)
    conn.cursor().execute(f'CREATE DATABASE "{name}"')
    conn.close()
    monkeypatch.setenv("DATABASE_URL", url.set(database=name).render_as_string(hide_password=False))
    get_settings.cache_clear()
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, REV)
    eng = sa.create_engine(url.set(drivername="postgresql+psycopg2", database=name))
    yield eng
    eng.dispose()
    get_settings.cache_clear()
    conn = _admin(url)
    conn.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    conn.close()


EXPECTED = {
    # name: (type, nullable)
    "id": ("UUID", False),
    "user_id": ("UUID", False),
    "community_id": ("UUID", False),
    "status": ("TEXT", False),
    "file_key": ("TEXT", True),
    "file_size_bytes": ("BIGINT", True),
    "error_message": ("TEXT", True),
    "created_at": ("TIMESTAMP", False),
    "ready_at": ("TIMESTAMP", True),
    "expires_at": ("TIMESTAMP", True),
    "downloaded_at": ("TIMESTAMP", True),
}


def test_columns_types_nullability(engine):
    cols = {c["name"]: c for c in sa.inspect(engine).get_columns("user_exports")}
    assert set(cols) == set(EXPECTED)
    for name, (typ, nullable) in EXPECTED.items():
        assert str(cols[name]["type"]).startswith(typ), name
        assert cols[name]["nullable"] is nullable, name
    for name in ("created_at", "ready_at", "expires_at", "downloaded_at"):
        assert cols[name]["type"].timezone is True, name


def test_defaults(engine):
    cols = {c["name"]: c for c in sa.inspect(engine).get_columns("user_exports")}
    assert "gen_random_uuid" in cols["id"]["default"]
    assert "pending" in cols["status"]["default"]
    assert "now()" in cols["created_at"]["default"]
    assert "00000000-0000-0000-0000-000000000001" in cols["community_id"]["default"]


def test_indexes(engine):
    idx = {i["name"]: i["column_names"] for i in sa.inspect(engine).get_indexes("user_exports")}
    assert idx["ix_user_exports_user_id_status"] == ["user_id", "status"]
    assert idx["ix_user_exports_expires_at"] == ["expires_at"]


def test_foreign_keys_cascade(engine):
    fks = {f["referred_table"]: f for f in sa.inspect(engine).get_foreign_keys("user_exports")}
    assert fks["users"]["options"].get("ondelete") == "CASCADE"
    assert fks["communities"]["options"].get("ondelete") == "CASCADE"
