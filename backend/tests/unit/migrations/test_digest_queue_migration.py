"""
@file tests/unit/migrations/test_digest_queue_migration.py
@brief Digest queue migration merges the dev heads into one (nexara#86).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]
REV = "0027_notification_digest_queue"


def test_digest_queue_migration_is_single_head_merging_parents() -> None:
    """@brief 0027 is the only head and descends from apprise + list_notified_at."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == [REV]
    assert set(script.get_revision(REV).down_revision) == {"b7c1d2e3f4a5", "e5f6a7b8c9d0"}
