"""
@file test_post_schemas.py
@brief Unit tests for post, comment, and reaction Pydantic schemas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.post import (
    CommentCreate,
    CommentResponse,
    PostAuthorResponse,
    PostCreate,
    PostResponse,
    ReactionResponse,
    ReactionToggle,
)


class TestPostCreate:
    """@brief PostCreate validation tests."""

    def test_valid_content(self):
        """PostCreate accepts valid content and optional media_ids."""
        req = PostCreate(content="Hello world")
        assert req.content == "Hello world"
        assert req.media_ids == []

    def test_valid_with_media_ids(self):
        """PostCreate accepts up to 10 media_ids."""
        ids = [uuid4() for _ in range(10)]
        req = PostCreate(content="Post with media", media_ids=ids)
        assert len(req.media_ids) == 10

    def test_empty_content_with_media_accepted(self):
        """PostCreate accepts empty content when media_ids are provided."""
        media_id = uuid4()
        req = PostCreate(content="", media_ids=[media_id])
        assert req.content == ""
        assert len(req.media_ids) == 1

    def test_no_content_no_media_rejected(self):
        """PostCreate rejects posts with neither content nor media."""
        with pytest.raises(ValidationError):
            PostCreate(content="", media_ids=[])

    def test_whitespace_only_no_media_rejected(self):
        """PostCreate rejects whitespace-only content with no media."""
        with pytest.raises(ValidationError):
            PostCreate(content="   ", media_ids=[])

    def test_max_length_rejected(self):
        """PostCreate rejects content over 10000 characters."""
        with pytest.raises(ValidationError):
            PostCreate(content="x" * 10001)

    def test_media_ids_max_10_rejected(self):
        """PostCreate rejects more than 10 media_ids."""
        with pytest.raises(ValidationError):
            PostCreate(content="Hi", media_ids=[uuid4() for _ in range(11)])


class TestCommentCreate:
    """@brief CommentCreate validation tests."""

    def test_valid_without_parent(self):
        """CommentCreate accepts content without parent_id."""
        req = CommentCreate(content="A comment")
        assert req.content == "A comment"
        assert req.parent_id is None

    def test_valid_with_parent_id(self):
        """CommentCreate accepts optional parent_id."""
        parent = uuid4()
        req = CommentCreate(content="A reply", parent_id=parent)
        assert req.parent_id == parent

    def test_min_length_rejected(self):
        """CommentCreate rejects empty content."""
        with pytest.raises(ValidationError):
            CommentCreate(content="")

    def test_max_length_rejected(self):
        """CommentCreate rejects content over 5000 characters."""
        with pytest.raises(ValidationError):
            CommentCreate(content="x" * 5001)


class TestReactionToggle:
    """@brief ReactionToggle validation tests."""

    def test_valid_emoji(self):
        """ReactionToggle accepts valid emoji string."""
        req = ReactionToggle(emoji="👍")
        assert req.emoji == "👍"

    def test_min_length_rejected(self):
        """ReactionToggle rejects empty emoji."""
        with pytest.raises(ValidationError):
            ReactionToggle(emoji="")


class TestPostResponse:
    """@brief PostResponse construction tests."""

    def test_from_dict(self):
        """PostResponse can be constructed from a dict-like structure."""
        post_id = uuid4()
        author_id = uuid4()
        now = datetime.now(UTC)
        resp = PostResponse(
            id=post_id,
            content="Test post",
            author=PostAuthorResponse(
                id=author_id,
                username="alice",
                display_name="Alice",
                avatar_url=None,
            ),
            media=[],
            reactions=[],
            comment_count=0,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == post_id
        assert resp.content == "Test post"
        assert resp.author.username == "alice"


class TestCommentResponse:
    """@brief CommentResponse construction tests."""

    def test_from_dict(self):
        """CommentResponse can be constructed from a dict-like structure."""
        comment_id = uuid4()
        author_id = uuid4()
        now = datetime.now(UTC)
        resp = CommentResponse(
            id=comment_id,
            content="A comment",
            author=PostAuthorResponse(
                id=author_id,
                username="bob",
                display_name="Bob",
                avatar_url=None,
            ),
            parent_id=None,
            created_at=now,
            replies=[],
        )
        assert resp.id == comment_id
        assert resp.content == "A comment"
        assert resp.parent_id is None


class TestReactionResponse:
    """@brief ReactionResponse construction tests."""

    def test_from_dict(self):
        """ReactionResponse can be constructed from a dict-like structure."""
        resp = ReactionResponse(action="added", emoji="👍", count=5)
        assert resp.action == "added"
        assert resp.emoji == "👍"
        assert resp.count == 5


class TestPostAuthorResponse:
    """@brief PostAuthorResponse from_attributes tests."""

    def test_from_attributes(self):
        """PostAuthorResponse can be built from model attributes."""
        author = type(
            "Author",
            (),
            {
                "id": uuid4(),
                "username": "charlie",
                "display_name": "Charlie",
                "avatar_url": "https://example.com/avatar.png",
            },
        )()
        resp = PostAuthorResponse.model_validate(author)
        assert resp.username == "charlie"
        assert resp.display_name == "Charlie"
        assert resp.avatar_url == "https://example.com/avatar.png"


class TestPostResponsePromptFlags:
    """@brief PostResponse prompt flag fields."""

    @staticmethod
    def _base() -> dict:
        now = datetime.now(UTC)
        return {
            "id": uuid4(),
            "content": "x",
            "author": {"id": uuid4(), "username": "a", "display_name": "A"},
            "created_at": now,
            "updated_at": now,
        }

    def test_defaults(self):
        """Prompt flags default to false/null."""
        resp = PostResponse(**self._base())
        assert resp.is_prompt_post is False
        assert resp.is_prompt_summary is False
        assert resp.reply_to_prompt_id is None
        assert resp.source_prompt_post_id is None

    def test_values_roundtrip(self):
        """Prompt flags are accepted and serialized."""
        pid = uuid4()
        resp = PostResponse(
            **self._base(),
            is_prompt_post=True,
            is_prompt_summary=True,
            reply_to_prompt_id=pid,
            source_prompt_post_id=pid,
        )
        dumped = resp.model_dump()
        assert dumped["is_prompt_post"] is True
        assert dumped["reply_to_prompt_id"] == pid
        assert dumped["source_prompt_post_id"] == pid
