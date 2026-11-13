"""
@file test_apprise_migration.py
@brief Migration c5d6e7f8a9b0: backfill apprise=false in notification_prefs.
"""

import json

import sqlalchemy as sa

from alembic import command
from tests.integration.migrations.test_notif_v2_foundation import _seed_user, scratch  # noqa: F401

REV = "c5d6e7f8a9b0"
PREV = "b2c3d4e5f6a7"


def _prefs(conn, uid):
    return conn.execute(
        sa.text("SELECT notification_prefs FROM user_settings WHERE user_id = :u"), {"u": uid}
    ).scalar_one()


def test_backfills_apprise_false_and_keeps_existing(scratch):  # noqa: F811
    cfg, engine = scratch
    command.upgrade(cfg, PREV)
    with engine.begin() as conn:
        uid = _seed_user(conn)
        empty = _seed_user(conn)
        conn.execute(
            sa.text("UPDATE user_settings SET notification_prefs = '{}' WHERE user_id = :u"),
            {"u": empty},
        )
        custom = json.dumps(
            {"mention": {"push": True, "apprise": True}, "comment": {"push": False}}
        )
        conn.execute(
            sa.text("UPDATE user_settings SET notification_prefs = CAST(:p AS jsonb) "
                    "WHERE user_id = :u"),
            {"p": custom, "u": uid},
        )  # fmt: skip
    command.upgrade(cfg, REV)
    with engine.begin() as conn:
        prefs = _prefs(conn, uid)
        assert prefs["mention"] == {"push": True, "apprise": True}
        assert prefs["comment"] == {"push": False, "apprise": False}
        assert _prefs(conn, empty) == {}


def test_no_new_columns_and_downgrade_strips(scratch):  # noqa: F811
    cfg, engine = scratch
    command.upgrade(cfg, PREV)
    with engine.begin() as conn:
        before = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'user_settings'")
            )
        }  # fmt: skip
        u = _seed_user(conn)
    command.upgrade(cfg, REV)
    with engine.begin() as conn:
        after = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'user_settings'")
            )
        }  # fmt: skip
        assert before == after
        assert all(v["apprise"] is False for v in _prefs(conn, u).values())
    command.downgrade(cfg, PREV)
    with engine.begin() as conn:
        assert all("apprise" not in v for v in _prefs(conn, u).values())
