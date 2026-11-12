"""
@file test_notif_v2_foundation.py
@brief Migration b2c3d4e5f6a7: schema add and JSONB prefs backfill (legacy columns kept).
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
REV = "b2c3d4e5f6a7"
PREV = "0028_plugin_pending_manifest"


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


def _cols(conn, table):
    rows = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table},
    )
    return {r[0] for r in rows}


def _seed_user(conn, **legacy):
    uid = uuid.uuid4()
    conn.execute(
        sa.text(
            "INSERT INTO users (id, email, username, display_name, password_hash) "
            "VALUES (:id, :e, :u, 'T', '!')"
        ),
        {"id": uid, "e": f"{uid}@e.test", "u": f"u{uid.hex[:8]}"},
    )
    names = ["user_id", *legacy]
    conn.execute(
        sa.text(
            f"INSERT INTO user_settings ({', '.join(names)}) "
            f"VALUES ({', '.join(':' + n for n in names)})"
        ),
        {"user_id": uid, **legacy},
    )
    return uid


def test_upgrade_adds_and_backfills(scratch):
    cfg, engine = scratch
    command.upgrade(cfg, PREV)
    with engine.begin() as conn:
        uid = _seed_user(
            conn,
            notif_mention_email=False,
            notif_reaction_email=True,
            notif_comment_push=False,
            notif_gallery_activity_email=True,
            notif_gallery_activity_push=True,
            mute_all_email=True,
        )
        default_uid = _seed_user(conn)

    command.upgrade(cfg, REV)

    with engine.begin() as conn:
        prefs = conn.execute(
            sa.text("SELECT notification_prefs FROM user_settings WHERE user_id = :u"),
            {"u": uid},
        ).scalar_one()
        assert len(prefs) == 12
        # mute_all_email forces email off for every type, beating overrides
        assert all(v["email"] is False for v in prefs.values())
        # legacy overrides win over type defaults
        assert prefs["mention"]["push"] is True
        assert prefs["comment"]["push"] is False
        # gallery_reminder follows the gallery_activity legacy values
        assert prefs["gallery_reminder"]["push"] is True
        assert prefs["reaction"]["inapp"] is True
        # missing combos fall back to section 5.1 defaults
        assert prefs["mention"]["toast"] is True
        assert all(set(v) == {"inapp", "email", "push", "toast"} for v in prefs.values())

        d = conn.execute(
            sa.text("SELECT notification_prefs FROM user_settings WHERE user_id = :u"),
            {"u": default_uid},
        ).scalar_one()
        assert d["mention"] == {"inapp": True, "email": True, "push": True, "toast": True}
        assert d["gallery_reminder"]["email"] is False  # follows gallery_activity default

        us = _cols(conn, "user_settings")
        assert {
            "notification_prefs", "dnd_schedule", "dnd_until", "dnd_timezone",
            "digest_cadence", "digest_last_sent_at",
        } <= us  # fmt: skip
        # legacy columns are retained until readers migrate
        assert {"notif_mention_email", "mute_all_email"} <= us
        assert {"group_key", "count", "actor_ids", "updated_at", "dismissed_at"} <= _cols(
            conn, "notifications"
        )
        idx = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT indexname FROM pg_indexes WHERE tablename = 'notifications'")
            )
        }
        assert {"notifications_group_active_idx", "notifications_user_active_idx"} <= idx
        assert (
            conn.execute(
                sa.text("SELECT dnd_timezone FROM user_settings WHERE user_id = :u"), {"u": uid}
            ).scalar_one()
            == "UTC"
        )


def test_downgrade_drops_v2_columns(scratch):
    cfg, engine = scratch
    command.upgrade(cfg, REV)
    command.downgrade(cfg, PREV)
    with engine.begin() as conn:
        us = _cols(conn, "user_settings")
        assert "notif_mention_inapp" in us and "mute_all_email" in us  # never dropped
        assert "notification_prefs" not in us
        assert "group_key" not in _cols(conn, "notifications")
