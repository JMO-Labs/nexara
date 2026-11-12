"""
@file test_bookmark.py
@brief Unit tests for the Bookmark model and 0023_bookmarks migration (AC1).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import UniqueConstraint

import app.models  # noqa: F401
from app.models.bookmark import Bookmark

BACKEND = Path(__file__).resolve().parents[3]
SRC = (BACKEND / "alembic" / "versions" / "0023_bookmarks.py").read_text()


class TestBookmarkModel:
    """@brief Model-level unique constraint."""

    def test_unique_user_post(self) -> None:
        names = {c.name for c in Bookmark.__table_args__ if isinstance(c, UniqueConstraint)}
        assert "uq_bookmarks_user_post" in names


class TestMigration:
    """@brief Migration merges previous heads and creates the expected schema."""

    def test_down_revision_covers_previous_heads(self) -> None:
        cfg = Config(str(BACKEND / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND / "alembic"))
        rev = ScriptDirectory.from_config(cfg).get_revision("0023_bookmarks")
        assert rev is not None
        assert set(rev.down_revision) == {"0020_add_recipient_to_posts", "0022_plugin_models"}

    def test_unique_constraint_and_index(self) -> None:
        assert 'UniqueConstraint("user_id", "post_id"' in SRC
        assert "ix_bookmarks_user_id" in SRC

    def test_downgrade_drops_table(self) -> None:
        down = SRC.split("def downgrade")[1]
        assert 'op.drop_table("bookmarks")' in down
