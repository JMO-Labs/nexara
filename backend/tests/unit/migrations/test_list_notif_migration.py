"""
@file tests/unit/migrations/test_list_notif_migration.py
@brief List notif email-defaults migration chains on the dev head (nexara#178).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]
REV = "0030_list_notif_email_defaults"


def test_list_notif_migration_follows_apprise_prefs() -> None:
    """@brief 0030_list_notif_email_defaults chains after c5d6e7f8a9b0, sole head."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == [REV]
    assert script.get_revision(REV).down_revision == "c5d6e7f8a9b0"
