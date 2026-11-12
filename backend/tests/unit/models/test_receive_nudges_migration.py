"""
@file test_receive_nudges_migration.py
@brief 0028_receive_nudges is the single head and the column is mapped (nexara#62).
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.user_settings import UserSettings

BACKEND = Path(__file__).resolve().parents[3]


def test_receive_nudges_migration_is_head() -> None:
    """@brief New migration chains after b2c3d4e5f6a7 (current dev head)."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0028_receive_nudges"]
    rev = script.get_revision("0028_receive_nudges")
    assert rev.down_revision == "b2c3d4e5f6a7"


def test_user_settings_has_receive_nudges_column() -> None:
    """@brief ORM maps receive_nudges as non-null, default true."""
    col = UserSettings.__table__.c.receive_nudges
    assert col.nullable is False
    assert str(col.server_default.arg) == "true"
