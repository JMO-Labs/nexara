"""
@file tests/unit/migrations/test_apprise_migration.py
@brief Apprise URLs migration chains on the current head (nexara#80).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def test_apprise_migration_follows_user_exports_on_single_head() -> None:
    """@brief b7c1d2e3f4a5 follows 0026_user_exports_table; graph has one head."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert "b7c1d2e3f4a5" in {r.revision for r in script.iterate_revisions(heads[0], "base")}
    assert script.get_revision("b7c1d2e3f4a5").down_revision == "0026_user_exports_table"


def test_apprise_prefs_migration_follows_dev_head() -> None:
    """@brief c5d6e7f8a9b0 chains after 0031_receive_nudges and is the sole head."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["c5d6e7f8a9b0"]
    assert script.get_revision("c5d6e7f8a9b0").down_revision == "0031_receive_nudges"
