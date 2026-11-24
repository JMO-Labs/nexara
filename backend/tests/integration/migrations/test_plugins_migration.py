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


def _run(engine, sql: str, **kw) -> None:
    with engine.begin() as conn:
        conn.execute(sa.text(sql), kw)


def test_constraints_and_indexes(scratch):  # noqa: F811
    cfg, engine = scratch
    command.upgrade(cfg, REV)
    insp = sa.inspect(engine)
    idx = {t: {i["name"]: i for i in insp.get_indexes(t)} for t in NEW}
    assert "ix_plugin_user_prefs_user" in idx["plugin_user_prefs"]
    assert "ix_plugin_communities_community" in idx["plugin_communities"]
    assert idx["plugin_tokens"]["uq_plugin_tokens_active"]["unique"]
    fks = {f["referred_table"] for f in insp.get_foreign_keys("plugin_communities")}
    assert {"plugin_installs", "users", "communities"} <= fks
    with pytest.raises(IntegrityError):  # tier CHECK
        _run(engine, "INSERT INTO plugin_installs (plugin_id, version, manifest, tier) "
                     "VALUES ('t', '1', '{}', 'gold')")  # fmt: skip
    _run(engine, "INSERT INTO plugin_installs (id, plugin_id, version, manifest) "
                 "VALUES (gen_random_uuid(), 'p', '1', '{}')")  # fmt: skip
    _run(engine, "INSERT INTO users (id, email, username, display_name) "
                 "VALUES (gen_random_uuid(), 'b@x.invalid', 'b', 'B')")  # fmt: skip
    _run(engine, "INSERT INTO communities (id, name) VALUES (gen_random_uuid(), 'c2')")
    ins = ("INSERT INTO plugin_communities (install_id, community_id, bot_user_id) "
           "SELECT i.id, c.id, u.id FROM plugin_installs i, communities c, users u "
           "WHERE i.plugin_id = 'p' AND u.username = 'b' AND c.name = :c")  # fmt: skip
    default = sa.text("SELECT name FROM communities WHERE id = :i")
    with engine.begin() as conn:
        first = conn.execute(default, {"i": "00000000-0000-0000-0000-000000000001"}).scalar()
    _run(engine, ins, c=first)
    with pytest.raises(IntegrityError):  # one bot per (install, community)
        _run(engine, ins, c="c2")
    tok = ("INSERT INTO plugin_tokens (install_id, token_hash) "
           "SELECT id, :h FROM plugin_installs WHERE plugin_id = 'p'")  # fmt: skip
    _run(engine, tok, h="h1")
    with pytest.raises(IntegrityError):  # one active token per (install, community)
        _run(engine, tok, h="h2")
    _run(engine, "UPDATE plugin_tokens SET revoked_at = now()")
    _run(engine, tok, h="h2")
