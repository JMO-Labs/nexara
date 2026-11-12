"""
@file tests/unit/migrations/test_apprise_migration.py
@brief Apprise URLs migration chains on the current head (nexara#80).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def test_apprise_migration_is_single_head_after_list_templates() -> None:
    """@brief b7c1d2e3f4a5 follows b2c3d4e5f6a7 and is the only head."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["b7c1d2e3f4a5"]
    assert script.get_revision("b7c1d2e3f4a5").down_revision == "b2c3d4e5f6a7"
