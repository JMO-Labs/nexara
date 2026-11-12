"""
@file tests/unit/migrations/test_single_head.py
@brief Guard: the alembic revision graph must have exactly one head.

Parallel PRs that each add a migration off the same parent create two heads,
which breaks `alembic upgrade head`. Re-point the newer migration's
down_revision to the other head to fix.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def test_single_alembic_head() -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert len(heads) == 1, f"multiple alembic heads {heads}: re-point down_revision to one head"
