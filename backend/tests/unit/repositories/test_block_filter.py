"""
@file test_block_filter.py
@brief Unit tests for BaseRepository.apply_block_filter().

Validates that the block filter correctly generates SQL that excludes
content from blocked users (bidirectional).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, Text, select
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.repositories.base import BaseRepository


class _FakePost(Base):
    """@brief Minimal model with user_id for testing block filter."""

    __tablename__ = "fake_posts_for_block_test"
    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text)


class _FakeNoAuthor(Base):
    """@brief Model without user_id/author_id for testing no-op fallback."""

    __tablename__ = "fake_no_author_for_block_test"
    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(Text)


class TestApplyBlockFilter:
    """@brief Tests for the static apply_block_filter method."""

    def test_adds_where_clauses_for_model_with_user_id(self):
        """apply_block_filter should add NOT IN subqueries for blocked users."""
        viewer_id = uuid.uuid4()
        stmt = select(_FakePost)

        filtered = BaseRepository.apply_block_filter(stmt, viewer_id)

        compiled = str(filtered.compile(compile_kwargs={"literal_binds": False}))
        assert "user_blocks" in compiled
        assert "NOT IN" in compiled.upper() or "NOT IN" in compiled

    def test_noop_for_model_without_author_column(self):
        """apply_block_filter should return stmt unchanged if no author column."""
        viewer_id = uuid.uuid4()
        stmt = select(_FakeNoAuthor)

        filtered = BaseRepository.apply_block_filter(stmt, viewer_id)

        original_str = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        filtered_str = str(filtered.compile(compile_kwargs={"literal_binds": False}))
        assert original_str == filtered_str

    def test_bidirectional_exclusion(self):
        """apply_block_filter should exclude both directions of blocking."""
        viewer_id = uuid.uuid4()
        stmt = select(_FakePost)

        filtered = BaseRepository.apply_block_filter(stmt, viewer_id)

        compiled = str(filtered.compile(compile_kwargs={"literal_binds": False}))
        assert compiled.count("user_blocks") >= 2, (
            "Should reference user_blocks at least twice for bidirectional filter"
        )
