"""
@file tests/unit/migrations/test_apprise_migration.py
@brief Apprise URLs migration chains on the current head (nexara#80).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def test_apprise_migration_is_single_head_after_list_templates() -> None:
    """@brief b7c1d2e3f4a5 follows 0026_user_exports_table and the tree has a single head."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert len(script.get_heads()) == 1
    assert script.get_revision("b7c1d2e3f4a5").down_revision == "0026_user_exports_table"
