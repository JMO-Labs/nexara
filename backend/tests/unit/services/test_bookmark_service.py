"""
@file test_bookmark_service.py
@brief Unit tests for BookmarkService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.bookmark import Bookmark
from app.repositories.bookmark_repo import BookmarkRepository
from app.repositories.post_repo import PostRepository
from app.services.bookmark_service import BookmarkService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
POST_ID = uuid.uuid4()


def _bookmark() -> MagicMock:
    b = MagicMock(spec=Bookmark)
    b.id = uuid.uuid4()
    b.user_id = USER_ID
    b.post_id = POST_ID
    b.created_at = datetime.now(UTC)
    return b


@pytest.fixture
def repos():
    repo = AsyncMock(spec=BookmarkRepository)
    posts = AsyncMock(spec=PostRepository)
    posts.get_post_detail.return_value = {"id": str(POST_ID)}
    repo.get_for_user_post.return_value = None
    repo.create_bookmark.return_value = _bookmark()
    return repo, posts


@pytest.fixture
def service(repos):
    return BookmarkService(repos[0], repos[1], COMMUNITY_ID)


async def test_toggle_creates_when_missing(service, repos):
    out = await service.toggle(POST_ID, USER_ID)
    assert out["is_bookmarked"] is True
    assert out["post_id"] == POST_ID
    assert out["created_at"] is not None
    repos[0].create_bookmark.assert_awaited_once()


async def test_toggle_removes_when_present(service, repos):
    repos[0].get_for_user_post.return_value = _bookmark()
    out = await service.toggle(POST_ID, USER_ID)
    assert out == {"post_id": POST_ID, "is_bookmarked": False, "created_at": None}
    repos[0].delete_bookmark.assert_awaited_once()
    repos[0].create_bookmark.assert_not_awaited()


async def test_toggle_unknown_post_404(service, repos):
    repos[1].get_post_detail.return_value = None
    with pytest.raises(NotFoundError):
        await service.toggle(POST_ID, USER_ID)


async def test_list_shapes_response(service, repos):
    b = _bookmark()
    repos[0].list_for_user.return_value = ([(b, {"id": str(POST_ID)})], "next")
    out = await service.list(USER_ID, None, 20)
    assert out["bookmarks"] == [
        {"id": b.id, "post": {"id": str(POST_ID)}, "bookmarked_at": b.created_at}
    ]
    assert out["pagination"] == {"cursor": "next", "has_more": True}


async def test_delete_own(service, repos):
    b = _bookmark()
    repos[0].get_by_id.return_value = b
    await service.delete(b.id, USER_ID)
    repos[0].delete_bookmark.assert_awaited_once_with(b)


async def test_delete_missing_404(service, repos):
    repos[0].get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await service.delete(uuid.uuid4(), USER_ID)


async def test_delete_other_users_403(service, repos):
    b = _bookmark()
    b.user_id = uuid.uuid4()
    repos[0].get_by_id.return_value = b
    with pytest.raises(AuthorizationError):
        await service.delete(b.id, USER_ID)
