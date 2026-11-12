"""
@file test_pronouns_migration.py
@brief Verify the pronouns migration sits on the single alembic head (nexara#34).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_pronouns_migration_follows_bookmarks_on_single_head() -> None:
    """@brief Pronouns revision chains after 0023_bookmarks with one head."""
    script = _script()
    heads = script.get_heads()
    assert len(heads) == 1
    rev = script.get_revision("0024_add_user_pronouns")
    assert rev.down_revision == "0023_bookmarks"
    ancestors = {r.revision for r in script.iterate_revisions(heads[0], "base")}
    assert "0024_add_user_pronouns" in ancestors
