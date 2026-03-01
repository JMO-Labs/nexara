"""
@file test_post_service.py
@brief Unit tests for PostService.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.services.realtime.events import EventType, FeedEvent
from tests.unit.services.conftest import (
    ADMIN_ID,
    AUTHOR_ID,
    COMMUNITY_ID,
    POST_ID,
    VIEWER_ID,
    _make_post,
    _make_user,
)


class TestListFeed:
    """@brief Tests for list_feed()."""

    @pytest.mark.asyncio
    async def test_list_feed_returns_paginated(self, service, post_repo):
        """list_feed() calls post_repo.list_feed and returns dict with items/cursor/has_more."""
        items = [{"id": str(POST_ID), "content": "Hello"}]
        post_repo.list_feed.return_value = (items, "cursor-123")
        result = await service.list_feed()
        assert result["items"] == items
        assert result["cursor"] == "cursor-123"
        assert result["has_more"] is True
        post_repo.list_feed.assert_awaited_once_with(
            COMMUNITY_ID, viewer_id=None, cursor=None, limit=20
        )

    @pytest.mark.asyncio
    async def test_list_feed_passes_viewer_id(self, service, post_repo):
        """list_feed() passes viewer_id to repo."""
        post_repo.list_feed.return_value = ([], None)
        await service.list_feed(viewer_id=VIEWER_ID, cursor="c", limit=10)
        post_repo.list_feed.assert_awaited_once_with(
            COMMUNITY_ID, viewer_id=VIEWER_ID, cursor="c", limit=10
        )


class TestGetPost:
    """@brief Tests for get_post()."""

    @pytest.mark.asyncio
    async def test_get_post_found(self, service, post_repo):
        """get_post() returns enriched dict when post exists."""
        enriched = {"id": str(POST_ID), "content": "Hi", "author": {}}
        post_repo.get_post_detail.return_value = enriched
        result = await service.get_post(POST_ID, viewer_id=VIEWER_ID)
        assert result == enriched
        post_repo.get_post_detail.assert_awaited_once_with(POST_ID, COMMUNITY_ID, VIEWER_ID)

    @pytest.mark.asyncio
    async def test_get_post_not_found(self, service, post_repo):
        """get_post() raises NotFoundError when post does not exist."""
        post_repo.get_post_detail.return_value = None
        with pytest.raises(NotFoundError):
            await service.get_post(POST_ID)


class TestCreatePost:
    """@brief Tests for create_post()."""

    @pytest.mark.asyncio
    async def test_create_post_basic(self, service, post_repo):
        """create_post() creates post and returns enriched dict."""
        user = _make_user()
        post = _make_post()
        post_repo.create_post.return_value = post
        enriched = {"id": str(post.id), "content": "Hello"}
        post_repo.get_post_detail.return_value = enriched
        result = await service.create_post(user, "Hello world")
        assert result == enriched
        post_repo.create_post.assert_awaited_once_with(
            author_id=user.id, content="Hello world", community_id=COMMUNITY_ID
        )
        post_repo.get_post_detail.assert_awaited_once_with(post.id, COMMUNITY_ID, user.id)

    @pytest.mark.asyncio
    async def test_create_post_with_media(self, service_with_media, post_repo, media_attacher):
        """create_post() calls media_attacher with media_ids."""
        user = _make_user()
        post = _make_post()
        post_repo.create_post.return_value = post
        post_repo.get_post_detail.return_value = {}
        media_ids = [uuid.uuid4(), uuid.uuid4()]
        await service_with_media.create_post(user, "Hi", media_ids=media_ids)
        media_attacher.assert_awaited_once_with(post.id, media_ids, user)

    @pytest.mark.asyncio
    async def test_create_post_emits_event(
        self,
        service_with_event_bus,
        post_repo,
        mock_event_bus,
    ):
        """create_post() emits a post_created event via EventBus."""
        user = _make_user()
        post = _make_post()
        enriched = {"id": str(post.id), "content": "Hi"}
        post_repo.create_post.return_value = post
        post_repo.get_post_detail.return_value = enriched
        await service_with_event_bus.create_post(user, "Hello")
        mock_event_bus.emit.assert_awaited_once()
        event = mock_event_bus.emit.call_args[0][0]
        assert event.type == EventType.FEED_UPDATE
        assert event.payload["event"] == FeedEvent.POST_CREATED
        assert event.payload["post"] == enriched

    @pytest.mark.asyncio
    async def test_create_post_delegates_mention_notifications(self, service, post_repo):
        """create_post() delegates mention detection to notification_service.notify_mentions."""
        user = _make_user()
        post = _make_post()
        post_repo.create_post.return_value = post
        post_repo.get_post_detail.return_value = {}
        await service.create_post(user, "Hey @bob!")
        service._notification.notify_mentions.assert_awaited_once_with(
            "Hey @bob!",
            user,
            post.id,
            post_repo._session,
        )


class TestDeletePost:
    """@brief Tests for delete_post()."""

    @pytest.mark.asyncio
    async def test_delete_post_by_author(self, service, post_repo):
        """delete_post() allows author to delete own post."""
        user = _make_user()
        post = _make_post(author_id=user.id)
        post_repo.get_by_id.return_value = post
        await service.delete_post(POST_ID, user)
        post_repo.soft_delete.assert_awaited_once_with(post)

    @pytest.mark.asyncio
    async def test_delete_post_by_admin(self, service, post_repo):
        """delete_post() allows admin to delete any post."""
        user = _make_user(user_id=ADMIN_ID, role="admin")
        post = _make_post(author_id=AUTHOR_ID)
        post_repo.get_by_id.return_value = post
        await service.delete_post(POST_ID, user)
        post_repo.soft_delete.assert_awaited_once_with(post)

    @pytest.mark.asyncio
    async def test_delete_post_unauthorized(self, service, post_repo):
        """delete_post() raises AuthorizationError when non-author non-admin."""
        user = _make_user(user_id=VIEWER_ID)
        post = _make_post(author_id=AUTHOR_ID)
        post_repo.get_by_id.return_value = post
        with pytest.raises(AuthorizationError):
            await service.delete_post(POST_ID, user)
        post_repo.soft_delete.assert_not_awaited()


class TestAddComment:
    """@brief Tests for add_comment()."""

    @pytest.mark.asyncio
    async def test_add_comment_notifies_post_author(self, service, post_repo, comment_repo):
        """add_comment() sends notification to post author."""
        user = _make_user(user_id=VIEWER_ID)
        post = _make_post(author_id=AUTHOR_ID)
        comment = MagicMock()
        comment.id = uuid.uuid4()
        comment.content = "Nice!"
        comment.parent_id = None
        comment.created_at = MagicMock()
        comment.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        post_repo.get_by_id.return_value = post
        comment_repo.create_comment.return_value = comment
        result = await service.add_comment(POST_ID, user, "Nice!")
        assert "id" in result
        service._notification.notify.assert_awaited()
        call_kwargs = service._notification.notify.call_args[1]
        assert call_kwargs["user_id"] == AUTHOR_ID
        assert call_kwargs["type"] == "comment"

    @pytest.mark.asyncio
    async def test_add_comment_to_missing_post(self, service, post_repo):
        """add_comment() raises NotFoundError when post does not exist."""
        user = _make_user()
        post_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.add_comment(POST_ID, user, "Hi")

    @pytest.mark.asyncio
    async def test_add_comment_emits_event(
        self,
        service_with_event_bus,
        post_repo,
        comment_repo,
        mock_event_bus,
    ):
        """add_comment() emits a comment_created event via EventBus."""
        user = _make_user(user_id=VIEWER_ID)
        post = _make_post(author_id=AUTHOR_ID)
        comment = MagicMock()
        comment.id = uuid.uuid4()
        comment.content = "Great!"
        comment.parent_id = None
        comment.created_at = MagicMock()
        comment.created_at.isoformat.return_value = "2026-02-28T10:00:00"
        post_repo.get_by_id.return_value = post
        comment_repo.create_comment.return_value = comment

        await service_with_event_bus.add_comment(POST_ID, user, "Great!")

        mock_event_bus.emit.assert_awaited()
        event = mock_event_bus.emit.call_args[0][0]
        assert event.type == EventType.FEED_UPDATE
        assert event.payload["event"] == FeedEvent.COMMENT_CREATED
        assert event.payload["post_id"] == str(POST_ID)
        assert event.payload["user_id"] == str(VIEWER_ID)
        assert event.payload["comment"]["content"] == "Great!"


class TestToggleReaction:
    """@brief Tests for toggle_reaction()."""

    @pytest.mark.asyncio
    async def test_toggle_reaction_added(self, service, post_repo, reaction_repo):
        """toggle_reaction() returns action=added when reaction is added."""
        user = _make_user()
        post = _make_post()
        post_repo.get_by_id.return_value = post
        reaction_repo.toggle.return_value = ("added", 1)
        result = await service.toggle_reaction(POST_ID, user, "\U0001f44d")
        assert result.action == "added"
        assert result.emoji == "\U0001f44d"
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_toggle_reaction_removed(self, service, post_repo, reaction_repo):
        """toggle_reaction() returns action=removed when reaction is removed."""
        user = _make_user()
        post = _make_post()
        post_repo.get_by_id.return_value = post
        reaction_repo.toggle.return_value = ("removed", 0)
        result = await service.toggle_reaction(POST_ID, user, "\U0001f44d")
        assert result.action == "removed"
        assert result.emoji == "\U0001f44d"
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_toggle_reaction_notifies_author(self, service, post_repo, reaction_repo):
        """toggle_reaction() sends notification on added, not on removed."""
        user = _make_user(user_id=VIEWER_ID)
        post = _make_post(author_id=AUTHOR_ID)
        post_repo.get_by_id.return_value = post
        reaction_repo.toggle.return_value = ("added", 1)
        await service.toggle_reaction(POST_ID, user, "\U0001f44d")
        service._notification.notify.assert_awaited_once()
        service._notification.reset_mock()
        reaction_repo.toggle.return_value = ("removed", 0)
        await service.toggle_reaction(POST_ID, user, "\U0001f44d")
        service._notification.notify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_toggle_reaction_emits_event(
        self,
        service_with_event_bus,
        post_repo,
        reaction_repo,
        mock_event_bus,
    ):
        """toggle_reaction() emits a reaction_toggled event via EventBus."""
        user = _make_user()
        post = _make_post()
        post_repo.get_by_id.return_value = post
        reaction_repo.toggle.return_value = ("added", 1)
        await service_with_event_bus.toggle_reaction(POST_ID, user, "\U0001f44d")
        mock_event_bus.emit.assert_awaited()
        event = mock_event_bus.emit.call_args[0][0]
        assert event.type == EventType.FEED_UPDATE
        assert event.payload["event"] == FeedEvent.REACTION_TOGGLED
        assert event.payload["emoji"] == "\U0001f44d"
        assert event.payload["count"] == 1
        assert event.payload["action"] == "added"
