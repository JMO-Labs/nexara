"""
@file test_models_content.py
@brief TDD tests for content models: Post, Comment, Reaction, Media, PostMedia.
"""

import app.models  # noqa: F401 — register all models with Base.metadata
from app.db.base import Base


def _get_table(name: str):
    """@brief Helper to retrieve a table from Base metadata by name."""
    return Base.metadata.tables.get(name)


def _get_columns(table_name: str) -> set[str]:
    """@brief Return the set of column names for a given table."""
    table = _get_table(table_name)
    assert table is not None, f"Table '{table_name}' not found in metadata"
    return {c.name for c in table.columns}


class TestPostModel:
    """@brief Verify the posts table schema."""

    def test_table_exists(self):
        assert _get_table("posts") is not None

    def test_required_columns(self):
        cols = _get_columns("posts")
        expected = {
            "id", "community_id", "uri", "author_id", "content",
            "visibility", "is_pinned", "deleted_at",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_fts_column(self):
        cols = _get_columns("posts")
        assert "content_fts" in cols

    def test_subgroup_column(self):
        cols = _get_columns("posts")
        assert "subgroup_id" in cols


class TestCommentModel:
    """@brief Verify the comments table schema."""

    def test_table_exists(self):
        assert _get_table("comments") is not None

    def test_required_columns(self):
        cols = _get_columns("comments")
        expected = {
            "id", "community_id", "post_id", "author_id",
            "parent_id", "content", "created_at",
        }
        assert expected.issubset(cols)


class TestReactionModel:
    """@brief Verify the reactions table schema."""

    def test_table_exists(self):
        assert _get_table("reactions") is not None

    def test_required_columns(self):
        cols = _get_columns("reactions")
        expected = {
            "id", "community_id", "user_id", "target_type",
            "target_id", "emoji", "created_at",
        }
        assert expected.issubset(cols)


class TestMediaModel:
    """@brief Verify the media table schema."""

    def test_table_exists(self):
        assert _get_table("media") is not None

    def test_required_columns(self):
        cols = _get_columns("media")
        expected = {
            "id", "community_id", "uploader_id", "filename",
            "content_type", "storage_key", "thumbnail_key",
            "size_bytes", "status", "created_at",
        }
        assert expected.issubset(cols)

    def test_dimension_columns(self):
        cols = _get_columns("media")
        assert {"width", "height", "duration_secs", "alt_text"}.issubset(cols)


class TestPostMediaModel:
    """@brief Verify the post_media junction table."""

    def test_table_exists(self):
        assert _get_table("post_media") is not None

    def test_composite_pk(self):
        table = _get_table("post_media")
        pk_names = {c.name for c in table.primary_key.columns}
        assert pk_names == {"post_id", "media_id"}

    def test_position_column(self):
        cols = _get_columns("post_media")
        assert "position" in cols
