"""
@file test_post_enrichment.py
@brief Unit tests for enrich_posts is_bookmarked flag (AC5).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.post import Post
from app.models.user import User
from app.repositories.post_enrichment import enrich_posts

POST_ID, AUTHOR_ID, VIEWER_ID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _rows() -> tuple[MagicMock, MagicMock]:
    """@brief Build mock (post, author) row."""
    post = MagicMock(spec=Post)
    post.id, post.content, post.subgroup_id = POST_ID, "hi", None
    post.created_at = post.updated_at = datetime.now(UTC)
    user = MagicMock(spec=User)
    user.id, user.username, user.display_name, user.avatar_url = AUTHOR_ID, "a", "A", None
    return post, user


def _empty() -> MagicMock:
    """@brief Result mock with no rows."""
    r = MagicMock()
    r.all.return_value = []
    r.scalars.return_value.all.return_value = []
    return r


def _posts() -> MagicMock:
    """@brief Result mock with one (post, author) row."""
    r = MagicMock()
    r.all.return_value = [_rows()]
    return r


class TestIsBookmarked:
    """@brief is_bookmarked is False for anonymous viewers or unbookmarked posts."""

    async def test_anonymous_viewer_is_false(self) -> None:
        session = AsyncMock()
        # posts, media, reactions, comments, polls (no viewer-only queries)
        session.execute = AsyncMock(side_effect=[_posts(), _empty(), _empty(), _empty(), _empty()])
        out = await enrich_posts(session, [POST_ID], None)
        assert out[POST_ID]["is_bookmarked"] is False

    async def test_viewer_without_bookmark_is_false(self) -> None:
        session = AsyncMock()
        # posts, media, reactions, my_reactions, comments, bookmarks, polls
        session.execute = AsyncMock(
            side_effect=[_posts(), _empty(), _empty(), _empty(), _empty(), _empty(), _empty()]
        )
        out = await enrich_posts(session, [POST_ID], VIEWER_ID)
        assert out[POST_ID]["is_bookmarked"] is False
