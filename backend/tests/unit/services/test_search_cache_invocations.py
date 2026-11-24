"""
@file test_search_cache_invocations.py
@brief Every mutating service path busts the search cache once (split from
       test_search_cache.py).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.birthday = None
    u.age_group = None
    return u


def _inv(module: str):
    """@brief Patch the invalidator as imported by a service module."""
    return patch(f"app.services.{module}.invalidate_search_cache_for_community", new=AsyncMock())


def _assert_inv(inv, service, action):
    """@brief Assert one invalidation with the expected service/action tags."""
    inv.assert_awaited_once()
    assert inv.await_args.args == (CID,)
    assert inv.await_args.kwargs["service"] == service
    assert inv.await_args.kwargs["action"] == action


def _post_service():
    from app.services.post_service import PostService

    repo = AsyncMock()
    repo.create_post.return_value = MagicMock(subgroup_id=None)
    repo.get_post_detail.return_value = {"id": "p"}
    repo.nsfw_hidden.return_value = False
    from app.repositories.tag_repo import TagRepository

    tags = AsyncMock(spec=TagRepository)
    tags.users_by_username.return_value = []
    tags.blocked_with.return_value = set()
    tags.replace_user_tags.return_value = []
    svc = PostService(repo, AsyncMock(), AsyncMock(), AsyncMock(), CID, tag_repo=tags)
    return svc, repo


def _event_service(owner):
    from app.services.event_service import EventService

    repo = AsyncMock()
    repo.get_by_id.return_value = MagicMock(author_id=owner)
    svc = EventService(repo, CID, AsyncMock(), calendar_service=AsyncMock(), token_repo=AsyncMock())
    svc._build_response = AsyncMock()  # type: ignore[method-assign]
    return svc


def _gallery_service(owner):
    from app.services.gallery_service import GalleryService

    repo = AsyncMock()
    repo.get_by_id.return_value = MagicMock(owner_id=owner, is_nsfw=False)
    repo.nsfw_media_among.return_value = set()
    return GalleryService(repo, CID, AsyncMock())


def _media_service(owner):
    from app.services.media_service import MediaService

    repo = AsyncMock()
    repo.get.return_value = MagicMock(uploader_id=owner, thumbnail_key=None)
    return MediaService(repo, AsyncMock(), AsyncMock(), CID)


class TestInvocationPoints:
    """@brief Each mutating service method awaits the invalidator once."""

    async def test_create_post_invalidates(self):
        svc, _ = _post_service()
        with _inv("post_service") as inv:
            await svc.create_post(_user(), "hello")
        _assert_inv(inv, "post", "create")

    async def test_update_post_invalidates(self):
        svc, repo = _post_service()
        user = _user()
        repo.get_by_id.return_value = MagicMock(author_id=user.id)
        with _inv("post_service") as inv:
            await svc.update_post(uuid.uuid4(), user, "edited")
        _assert_inv(inv, "post", "update")

    async def test_delete_post_invalidates(self):
        svc, repo = _post_service()
        user = _user()
        repo.get_by_id.return_value = MagicMock(author_id=user.id)
        with _inv("post_service") as inv:
            await svc.delete_post(uuid.uuid4(), user)
        _assert_inv(inv, "post", "delete")

    async def test_create_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        data = MagicMock(
            recurrence_rule=None, visibility="community", contribution_slots=[], description=None
        )
        with _inv("event_service") as inv:
            await svc.create_event(uid, data)
        _assert_inv(inv, "event", "create")

    async def test_update_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        data = MagicMock()
        data.model_dump.return_value = {"title": "x"}
        with _inv("event_service") as inv:
            await svc.update_event(uuid.uuid4(), uid, data)
        _assert_inv(inv, "event", "update")

    async def test_delete_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        with _inv("event_service") as inv:
            await svc.delete_event(uuid.uuid4(), uid)
        _assert_inv(inv, "event", "delete")

    async def test_create_gallery_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        data = MagicMock(visibility="community")
        with _inv("gallery_service") as inv, patch("app.services.gallery_base.GalleryResponse"):
            await svc.create_gallery(uid, data)
        _assert_inv(inv, "gallery", "create")

    async def test_update_gallery_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        data = MagicMock()
        data.model_dump.return_value = {"title": "x"}
        with _inv("gallery_service") as inv, patch("app.services.gallery_base.GalleryResponse"):
            await svc.update_gallery(uuid.uuid4(), uid, data)
        _assert_inv(inv, "gallery", "update")

    async def test_add_gallery_item_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        svc._can_contribute = AsyncMock(return_value=True)  # type: ignore[method-assign]
        svc._repo.get_item.return_value = None
        data = MagicMock(position=None)
        with _inv("gallery_items") as inv, patch("app.services.gallery_base.GalleryResponse"):
            with patch("app.services.gallery_items.GalleryItemResponse"):
                await svc.add_item(uuid.uuid4(), uid, data)
        _assert_inv(inv, "gallery", "add_item")

    async def test_bulk_add_gallery_items_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        svc._repo.get_by_id.return_value = MagicMock(owner_id=uid, item_count=0)
        svc._can_contribute = AsyncMock(return_value=True)  # type: ignore[method-assign]
        svc._repo.get_item.return_value = None
        data = MagicMock(media_ids=[uuid.uuid4(), uuid.uuid4()])
        with _inv("gallery_items") as inv:
            with patch("app.services.gallery_items.GalleryItemResponse"):
                await svc.bulk_add_items(uuid.uuid4(), uid, data)
        _assert_inv(inv, "gallery", "add_item")

    async def test_delete_gallery_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        with _inv("gallery_service") as inv:
            await svc.delete_gallery(uuid.uuid4(), uid)
        _assert_inv(inv, "gallery", "delete")

    async def test_add_comment_invalidates(self):
        svc, repo = _post_service()
        repo.get_by_id.return_value = MagicMock(author_id=uuid.uuid4())
        svc._comment_repo.create_comment.return_value = MagicMock(
            id=uuid.uuid4(), parent_id=None, content="c", created_at=datetime.now(UTC)
        )
        svc._notify_comment_participants = AsyncMock()  # type: ignore[method-assign]
        svc._notify_mentions = AsyncMock()  # type: ignore[method-assign]
        with _inv("post_comments") as inv:
            await svc.add_comment(uuid.uuid4(), _user(), "hi")
        _assert_inv(inv, "comment", "create")

    async def test_upload_media_invalidates(self):
        user = _user()
        svc = _media_service(user.id)
        mod = "app.services.media_service"
        with (
            _inv("media_service") as inv,
            patch(f"{mod}.check_quota", new=AsyncMock()),
            patch(f"{mod}.increment_storage_used", new=AsyncMock()),
            patch(f"{mod}.generate_thumbnail"),
            patch(f"{mod}.enqueue_ocr"),
            patch(f"{mod}.MediaResponse"),
        ):
            await svc.upload(user, b"img", "a.png", "image/png", 3)
        _assert_inv(inv, "media", "create")

    async def test_delete_media_invalidates(self):
        user = _user()
        svc = _media_service(user.id)
        with (
            _inv("media_service") as inv,
            patch("app.services.media_service.decrement_storage_used", new=AsyncMock()),
        ):
            await svc.delete(uuid.uuid4(), user)
        _assert_inv(inv, "media", "delete")


class TestMediaReady:
    async def test_multipart_complete_invalidates(self):
        user = _user()
        sess = {"user_id": str(user.id), "content_type": "image/png", "filename": "a.png"}
        sess["parts"] = {"1": "etag"}
        valkey = AsyncMock()
        valkey.get.return_value = json.dumps(sess)
        storage = AsyncMock()
        storage.get.return_value = b"x"
        mod = "app.services.media.multipart"
        with (
            patch(f"{mod}.invalidate_search_cache_for_community", new=AsyncMock()) as inv,
            patch(f"{mod}.generate_thumbnail"),
            patch(f"{mod}.MediaResponse"),
            patch(f"{mod}.increment_storage_used", new=AsyncMock()),
        ):
            from app.services.media import multipart

            await multipart.complete_multipart_upload(
                AsyncMock(), storage, AsyncMock(), CID, valkey, user, "u1"
            )
        _assert_inv(inv, "media", "create")
