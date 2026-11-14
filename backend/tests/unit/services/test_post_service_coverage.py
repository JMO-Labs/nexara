"""
@file test_post_service_coverage.py
@brief Covers comment listing, parent checks, reaction not-found and reply notices.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from tests.unit.services.conftest import (
    AUTHOR_ID,
    POST_ID,
    VIEWER_ID,
    _make_post,
    _make_user,
)


def _comment(post_id=POST_ID, author_id=AUTHOR_ID):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.post_id = post_id
    c.author_id = author_id
    c.content = "x"
    c.parent_id = None
    c.created_at.isoformat.return_value = "2025-01-01T00:00:00"
    return c


class TestListComments:
    @pytest.mark.asyncio
    async def test_returns_page(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.list_for_post.return_value = ([{"id": "1"}], "next")
        result = await service.list_comments(POST_ID, VIEWER_ID, limit=5)
        assert result == {"items": [{"id": "1"}], "cursor": "next", "has_more": True}

    @pytest.mark.asyncio
    async def test_last_page_has_no_more(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.list_for_post.return_value = ([], None)
        result = await service.list_comments(POST_ID)
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_missing_post(self, service, post_repo):
        post_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.list_comments(POST_ID)


class TestAddCommentParent:
    @pytest.mark.asyncio
    async def test_missing_parent(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.add_comment(POST_ID, _make_user(), "hi", parent_id=uuid.uuid4())
        comment_repo.create_comment.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_parent_on_other_post(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.get_by_id.return_value = _comment(post_id=uuid.uuid4())
        with pytest.raises(NotFoundError):
            await service.add_comment(POST_ID, _make_user(), "hi", parent_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_reply_notifies_parent_author(self, service, post_repo, comment_repo):
        parent = _comment(author_id=AUTHOR_ID)
        post_repo.get_by_id.return_value = _make_post(author_id=uuid.uuid4())
        comment_repo.get_by_id.return_value = parent
        comment_repo.create_comment.return_value = _comment()
        await service.add_comment(POST_ID, _make_user(user_id=VIEWER_ID), "re", parent.id)
        calls = service._notification.notify.await_args_list
        assert any(
            c.kwargs["user_id"] == AUTHOR_ID and "replied" in c.kwargs["payload"]["message"]
            for c in calls
        )

    @pytest.mark.asyncio
    async def test_sassybot_enqueued(self, service, post_repo, comment_repo, sassybot_delay):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.create_comment.return_value = _comment()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        post_repo._session.execute.return_value = result
        await service.add_comment(POST_ID, _make_user(), "hey @sassybot")
        sassybot_delay.assert_called_once()


class TestReactionNotFound:
    @pytest.mark.asyncio
    async def test_post_reaction_missing_post(self, service, post_repo, reaction_repo):
        post_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.toggle_reaction(POST_ID, _make_user(), "👍")
        reaction_repo.toggle.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_comment_reaction_missing_post(self, service, post_repo):
        post_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.toggle_comment_reaction(POST_ID, uuid.uuid4(), _make_user(), "👍")

    @pytest.mark.asyncio
    async def test_comment_reaction_missing_comment(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.toggle_comment_reaction(POST_ID, uuid.uuid4(), _make_user(), "👍")

    @pytest.mark.asyncio
    async def test_comment_reaction_wrong_post(self, service, post_repo, comment_repo):
        post_repo.get_by_id.return_value = _make_post()
        comment_repo.get_by_id.return_value = _comment(post_id=uuid.uuid4())
        with pytest.raises(NotFoundError):
            await service.toggle_comment_reaction(POST_ID, uuid.uuid4(), _make_user(), "👍")
