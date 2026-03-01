"""
@file test_post_repo.py
@brief Unit tests for PostRepository, CommentRepository, and ReactionRepository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.post import Comment, Post, Reaction
from app.models.user import User
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.post_repo import PostRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR_ID, POST_ID, VIEWER_ID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestPostRepositoryCreatePost:
    """@brief Tests for PostRepository.create_post()."""

    @pytest.mark.asyncio
    async def test_creates_post_with_author_and_content(self):
        """create_post should insert a post with author_id, content, community_id."""
        session = _make_session()
        repo = PostRepository(session)

        result = await repo.create_post(
            author_id=AUTHOR_ID,
            content="Hello world",
            community_id=COMMUNITY_ID,
        )
        assert isinstance(result, Post)
        assert result.author_id == AUTHOR_ID
        assert result.content == "Hello world"
        assert result.community_id == COMMUNITY_ID
        session.add.assert_called_once()
        session.flush.assert_awaited()
        session.refresh.assert_awaited_once()


class TestPostRepositorySoftDeletePost:
    """@brief Tests for PostRepository.soft_delete_post()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_post_deleted(self):
        """soft_delete_post should return True when post exists and is deleted."""
        session = _make_session()
        post = MagicMock(spec=Post)
        post.id = POST_ID
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = post
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostRepository(session)
        result = await repo.soft_delete_post(POST_ID, COMMUNITY_ID)

        assert result is True
        session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_returns_false_when_post_not_found(self):
        """soft_delete_post should return False when post does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostRepository(session)
        result = await repo.soft_delete_post(POST_ID, COMMUNITY_ID)

        assert result is False


class TestPostRepositoryListFeed:
    """@brief Tests for PostRepository.list_feed()."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_posts(self):
        """list_feed should return empty list and None cursor when no posts."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostRepository(session)
        items, next_cursor = await repo.list_feed(COMMUNITY_ID)

        assert items == []
        assert next_cursor is None
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_enriched_posts_with_cursor(self):
        """list_feed should return enriched posts and next_cursor when limit+1 exist."""
        session = _make_session()
        now = datetime.now(UTC)
        post = MagicMock(spec=Post)
        post.id, post.content = POST_ID, "Test post"
        post.created_at = post.updated_at = now
        post2 = MagicMock(spec=Post)
        post2.id, post2.content = uuid.uuid4(), "Second"
        post2.created_at = post2.updated_at = now
        user = MagicMock(spec=User)
        user.id, user.username, user.display_name, user.avatar_url = (
            AUTHOR_ID,
            "alice",
            "Alice",
            None,
        )

        mock_list = MagicMock()
        mock_list.scalars.return_value.all.return_value = [post, post2, post2]
        mock_posts = MagicMock()
        mock_posts.all.return_value = [(post, user), (post2, user)]
        mock_empty = MagicMock()
        mock_empty.all.return_value = []
        mock_comments = MagicMock()
        mock_comments.all.return_value = [(POST_ID, 0), (post2.id, 0)]

        session.execute = AsyncMock(
            side_effect=[mock_list, mock_posts, mock_empty, mock_empty, mock_comments]
        )
        repo = PostRepository(session)
        items, next_cursor = await repo.list_feed(COMMUNITY_ID, limit=2)

        assert len(items) == 2
        assert items[0]["id"] == str(POST_ID)
        assert items[0]["author"]["username"] == "alice"
        assert next_cursor is not None


class TestPostRepositoryGetPostDetail:
    """@brief Tests for PostRepository.get_post_detail()."""

    @pytest.mark.asyncio
    async def test_returns_none_when_post_not_found(self):
        """get_post_detail should return None when post does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = PostRepository(session)
        result = await repo.get_post_detail(POST_ID, COMMUNITY_ID)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_enriched_post_when_found(self):
        """get_post_detail should return enriched post dict when found."""
        session = _make_session()
        post = MagicMock(spec=Post)
        post.id, post.content = POST_ID, "Test content"
        user = MagicMock(spec=User)
        user.id, user.username, user.display_name, user.avatar_url = (
            AUTHOR_ID,
            "bob",
            "Bob",
            None,
        )
        mock_get = MagicMock()
        mock_get.scalar_one_or_none.return_value = post
        mock_posts = MagicMock()
        mock_posts.all.return_value = [(post, user)]
        mock_empty = MagicMock()
        mock_empty.all.return_value = []
        mock_comments = MagicMock()
        mock_comments.all.return_value = [(POST_ID, 0)]

        session.execute = AsyncMock(
            side_effect=[mock_get, mock_posts, mock_empty, mock_empty, mock_comments]
        )
        repo = PostRepository(session)
        result = await repo.get_post_detail(POST_ID, COMMUNITY_ID)

        assert result is not None
        assert result["id"] == str(POST_ID)
        assert result["author"]["username"] == "bob"


class TestCommentRepository:
    """@brief Tests for CommentRepository."""

    @pytest.mark.asyncio
    async def test_create_comment_adds_and_flushes(self):
        """create_comment should add comment, flush, and accept optional parent_id."""
        session = _make_session()
        repo = CommentRepository(session)

        result = await repo.create_comment(
            post_id=POST_ID,
            author_id=AUTHOR_ID,
            content="A comment",
            community_id=COMMUNITY_ID,
        )

        assert isinstance(result, Comment)
        assert result.post_id == POST_ID
        assert result.content == "A comment"
        assert result.parent_id is None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

        parent_id = uuid.uuid4()
        result2 = await repo.create_comment(
            post_id=POST_ID,
            author_id=AUTHOR_ID,
            content="Reply",
            community_id=COMMUNITY_ID,
            parent_id=parent_id,
        )
        assert result2.parent_id == parent_id

    @pytest.mark.asyncio
    async def test_list_for_post_returns_comment_dicts(self):
        """list_for_post should return list of comment dicts with reactions."""
        session = _make_session()
        comment = MagicMock(spec=Comment)
        comment.id, comment.content, comment.parent_id = uuid.uuid4(), "Hi", None
        comment.created_at = datetime.now(UTC)
        user = MagicMock(spec=User)
        user.id, user.username, user.display_name, user.avatar_url = (
            AUTHOR_ID,
            "charlie",
            "Charlie",
            None,
        )
        comments_result = MagicMock()
        comments_result.all.return_value = [(comment, user)]
        reactions_result = MagicMock()
        reactions_result.all.return_value = []
        session.execute = AsyncMock(side_effect=[comments_result, reactions_result])

        repo = CommentRepository(session)
        comments, next_cursor = await repo.list_for_post(POST_ID)

        assert len(comments) == 1
        assert comments[0]["author"]["username"] == "charlie"
        assert comments[0]["reactions"] == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_comment_or_none(self):
        """get_by_id should return comment when found, None when not."""
        session = _make_session()
        comment = MagicMock(spec=Comment)
        comment.id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        session.execute = AsyncMock(return_value=mock_result)

        repo = CommentRepository(session)
        assert await repo.get_by_id(comment.id) is comment

        mock_result.scalar_one_or_none.return_value = None
        assert await repo.get_by_id(uuid.uuid4()) is None


class TestReactionRepository:
    """@brief Tests for ReactionRepository.toggle()."""

    @pytest.mark.asyncio
    async def test_toggle_adds_when_not_exists(self):
        """toggle should add reaction and return ('added', count) when none exists."""
        session = _make_session()
        mock_get = MagicMock()
        mock_get.scalar_one_or_none.return_value = None
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 1
        session.execute = AsyncMock(side_effect=[mock_get, mock_count])

        repo = ReactionRepository(session)
        action, count = await repo.toggle(
            user_id=VIEWER_ID,
            target_type="post",
            target_id=POST_ID,
            emoji="👍",
            community_id=COMMUNITY_ID,
        )

        assert action == "added"
        assert count == 1
        session.add.assert_called_once()
        session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_toggle_removes_when_exists(self):
        """toggle should remove reaction and return ('removed', count) when exists."""
        session = _make_session()
        existing = MagicMock(spec=Reaction)
        mock_get = MagicMock()
        mock_get.scalar_one_or_none.return_value = existing
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        session.execute = AsyncMock(side_effect=[mock_get, mock_count])

        repo = ReactionRepository(session)
        action, count = await repo.toggle(
            user_id=VIEWER_ID,
            target_type="post",
            target_id=POST_ID,
            emoji="👍",
            community_id=COMMUNITY_ID,
        )

        assert action == "removed"
        assert count == 0
        session.delete.assert_awaited_once_with(existing)
        session.add.assert_not_called()
