"""
@file tests/unit/migrations/test_digest_queue_migration.py
@brief Digest queue migration merges the dev heads into one (nexara#86).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]
REV = "0027_notification_digest_queue"


def test_digest_queue_migration_is_single_head_after_merge() -> None:
    """@brief Graph has one head and 0027 follows dev's 0030_merge_heads."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert len(script.get_heads()) == 1
    assert script.get_revision(REV).down_revision == "0030_merge_heads"
