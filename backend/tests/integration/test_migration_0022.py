"""
@file tests/integration/test_migration_0022.py
@brief Round-trip (upgrade, downgrade, upgrade) of migration 0022 on real Postgres.

Runs in a scratch database so the shared test DB is never downgraded.
"""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
PREV = "0021_add_subgroup_accent_color"
REV = "0022_list_templates"
TABLES = [
    "list_template",
    "list_template_field",
    "list_template_item",
    "list",
    "list_member",
    "list_item",
    "list_item_signup",
    "list_item_completion",
]
NOTIF = [
    f"notif_list_{k}_{ch}"
    for k in ("item", "signup", "completed", "expiring", "member")
    for ch in ("inapp", "email")
]


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


def _state(engine) -> tuple[set[str], set[str]]:
    insp = inspect(engine)
    tables = {t for t in TABLES if insp.has_table(t)}
    cols = {c["name"] for c in insp.get_columns("user_settings")} & set(NOTIF)
    return tables, cols


def _current(engine) -> set[str]:
    """@brief Return the set of revisions stamped in alembic_version."""
    with engine.connect() as c:
        return set(c.execute(text("SELECT version_num FROM alembic_version")).scalars())


def _counts(engine) -> tuple[int, int, int]:
    with engine.connect() as c:
        communities = c.execute(text("SELECT count(*) FROM communities")).scalar_one()
        tpl = c.execute(text("SELECT count(*) FROM list_template WHERE is_system")).scalar_one()
        fields = c.execute(text("SELECT count(*) FROM list_template_field")).scalar_one()
    return communities, tpl, fields


def test_upgrade_downgrade_upgrade_and_seed_dedup(scratch_db) -> None:
    cfg = _cfg()
    engine = scratch_db
    command.upgrade(cfg, PREV)
    with engine.begin() as c:  # a second community, so seeding is per community
        c.execute(
            text(
                "INSERT INTO communities (id, name, slug) VALUES (gen_random_uuid(), 'B', 'b-mig')"
            )
        )
    command.upgrade(cfg, "head")

    assert _current(engine) == {REV}
    assert _state(engine) == (set(TABLES), set(NOTIF))
    communities, tpl, fields = _counts(engine)
    assert communities >= 2
    assert tpl == 4 * communities
    assert fields == (5 + 5 + 4 + 6) * communities

    # Re-running the seed must not duplicate templates or fields.
    spec = importlib.util.spec_from_file_location(
        "mig0022", ROOT / "alembic" / "versions" / "0022_list_templates.py"
    )
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig._seed()
    assert _counts(engine) == (communities, tpl, fields)

    command.downgrade(cfg, PREV)
    assert _state(engine) == (set(), set())

    command.upgrade(cfg, "head")
    assert _state(engine) == (set(TABLES), set(NOTIF))
    assert _counts(engine) == (communities, tpl, fields)
