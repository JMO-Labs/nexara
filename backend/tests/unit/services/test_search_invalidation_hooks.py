"""
@file test_search_invalidation_hooks.py
@brief Event/gallery/post mutations invalidate the search cache.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.event_repo import EventRepository
from app.repositories.gallery_repo import GalleryRepository
from app.schemas.gallery import GalleryUpdate
from app.services.event_service import EventService
from app.services.gallery_service import GalleryService
from tests.unit.services.conftest import COMMUNITY_ID, POST_ID, _make_post, _make_user


@pytest.mark.asyncio
async def test_delete_event_invalidates_search_cache() -> None:
    repo = AsyncMock(spec=EventRepository)
    event = MagicMock()
    event.author_id = uuid.uuid4()
    repo.get_by_id.return_value = event
    session = AsyncMock()
    svc = EventService(repo, COMMUNITY_ID, session)
    with patch("app.services.event_service.invalidate_search_cache_for_community") as inv:
        await svc.delete_event(uuid.uuid4(), event.author_id)
    inv.assert_awaited_once_with(COMMUNITY_ID)


@pytest.mark.asyncio
async def test_update_gallery_invalidates_search_cache() -> None:
    repo = AsyncMock(spec=GalleryRepository)
    owner = uuid.uuid4()
    gallery = MagicMock()
    gallery.owner_id = owner
    repo.get_by_id.return_value = gallery
    svc = GalleryService(gallery_repo=repo, community_id=COMMUNITY_ID, session=AsyncMock())
    with (
        patch("app.services.gallery_service.invalidate_search_cache_for_community") as inv,
        patch("app.services.gallery_service.GalleryResponse") as resp,
    ):
        await svc.update_gallery(uuid.uuid4(), owner, GalleryUpdate(title="New"))
    inv.assert_awaited_once_with(COMMUNITY_ID)
    resp.model_validate.assert_called_once()


@pytest.mark.asyncio
async def test_update_post_invalidates_search_cache(service, post_repo) -> None:
    post = _make_post()
    post_repo.get_by_id.return_value = post
    post_repo.get_post_detail.return_value = {"id": str(POST_ID)}
    with patch("app.services.post_service.invalidate_search_cache_for_community") as inv:
        await service.update_post(post.id, _make_user(user_id=post.author_id), "edited")
    inv.assert_awaited_once_with(COMMUNITY_ID)
