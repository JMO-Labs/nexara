"""
@file tests/unit/migrations/test_home_glass_migration.py
@brief Home glass bento migration chains after 0030 and is the sole head.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]
REV = "0032_home_glass_bento"


def test_migration_parent_and_head() -> None:
    """@brief 0032 revises 0030_list_notif_email_defaults."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(REV)
    assert rev is not None
    assert rev.down_revision == "0030_list_notif_email_defaults"
