"""
@file test_plugins_migration.py
@brief 0076_plugins round trip on real Postgres.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from alembic import command
from tests.integration.migrations.test_notif_v2_foundation import scratch  # noqa: F401

REV = "0076_plugins"
PREV = "0075_countdowns"
NEW = {"plugin_installs", "plugin_communities", "plugin_tokens", "plugin_user_prefs",
       "plugin_indexes"}  # fmt: skip
OLD = {"plugins", "plugin_data", "plugin_api_keys"}


def _tables(engine):
    return set(sa.inspect(engine).get_table_names())


def test_round_trip_and_status_check(scratch):  # noqa: F811
    cfg, engine = scratch
    command.upgrade(cfg, PREV)
    assert OLD <= _tables(engine)
    command.upgrade(cfg, REV)
    t = _tables(engine)
    assert NEW <= t and not (OLD & t)
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO plugin_installs (plugin_id, version, manifest, status) "
                    "VALUES ('x', '1', '{}', 'weird')")
        )  # fmt: skip
    with engine.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO plugin_installs (plugin_id, version, manifest) "
                    "VALUES ('x', '1', '{}')")
        )  # fmt: skip
    command.downgrade(cfg, PREV)
    t = _tables(engine)
    assert OLD <= t and not (NEW & t)
    cols = {c["name"] for c in sa.inspect(engine).get_columns("posts")}
    assert "plugin_flags" not in cols
    command.upgrade(cfg, REV)
    assert NEW <= _tables(engine)
    cols = {c["name"] for c in sa.inspect(engine).get_columns("posts")}
    assert "plugin_flags" in cols
