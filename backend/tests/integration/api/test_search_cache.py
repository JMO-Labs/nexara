"""
@file test_search_cache.py
@brief Tests for the Valkey search-result cache and its invalidation.
"""

from __future__ import annotations

import fnmatch
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import invalidate_search_cache_for_community
from app.services.search_service import SearchService, search_cache_key

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeRedis:
    """@brief Minimal in-memory async Redis double (get/setex/expire/scan/delete)."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key):
        return self.data.get(key)

    async def setex(self, key, ttl, value):
        self.data[key] = value
        self.ttl[key] = ttl

    async def expire(self, key, ttl):
        self.ttl[key] = ttl
        return True

    async def scan(self, cursor=0, match=None, count=None):
        return 0, [k for k in self.data if fnmatch.fnmatch(k, match or "*")]

    async def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)
        return len(keys)


class BrokenRedis:
    """@brief Redis double where every call raises."""

    def __getattr__(self, name):
        async def boom(*a, **k):
            raise ConnectionError("down")

        return boom


def _service(redis):
    repo = AsyncMock()
    repo.search_posts.return_value = ([], None, 0)
    return SearchService(repo, CID, cache_client=redis), repo


def _user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.birthday = None
    return u


async def _search(svc, user, q="hello", cursor=None):
    return await svc.search(q, user, ["posts"], cursor, 20)


class TestKey:
    def test_stable_and_normalized(self):
        u = uuid.uuid4()
        a = search_cache_key(" Hello ", CID, ["users", "posts"], u, None)
        b = search_cache_key("hello", CID, ["posts", "users"], u, "0")
        assert a == b
        assert a.startswith("search:") and a.endswith(":0")

    def test_differs_per_user_and_query(self):
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        k = search_cache_key("hello", CID, ["posts"], u1, None)
        assert k != search_cache_key("hello", CID, ["posts"], u2, None)
        assert k != search_cache_key("world", CID, ["posts"], u1, None)

    def test_cursor_in_key(self):
        u = uuid.uuid4()
        assert search_cache_key("hi", CID, ["posts"], u, "abc").endswith(":abc")


class TestSearchCache:
    async def test_repeated_query_served_from_cache(self):
        redis = FakeRedis()
        svc, repo = _service(redis)
        user = _user()
        first = await _search(svc, user)
        second = await _search(svc, user)
        assert first == second
        assert repo.search_posts.await_count == 1
        (key,) = redis.data
        assert redis.ttl[key] == 60
        json.loads(redis.data[key])

    async def test_hit_resets_ttl(self):
        redis = FakeRedis()
        svc, _ = _service(redis)
        user = _user()
        await _search(svc, user)
        (key,) = redis.data
        redis.ttl[key] = 5
        await _search(svc, user)
        assert redis.ttl[key] == 60

    async def test_miss_after_invalidation_refetches(self):
        redis = FakeRedis()
        svc, repo = _service(redis)
        user = _user()
        await _search(svc, user)
        assert await invalidate_search_cache_for_community(CID, client=redis) == 1
        await _search(svc, user)
        assert repo.search_posts.await_count == 2

    async def test_cursor_pages_not_cached(self):
        redis = FakeRedis()
        svc, repo = _service(redis)
        user = _user()
        await _search(svc, user, cursor="abc")
        await _search(svc, user, cursor="abc")
        assert redis.data == {}
        assert repo.search_posts.await_count == 2

    async def test_valkey_down_falls_back_to_repo(self):
        svc, repo = _service(BrokenRedis())
        await _search(svc, _user())
        assert repo.search_posts.await_count == 1

    async def test_no_client_falls_back_to_repo(self):
        svc, repo = _service(None)
        await _search(svc, _user())
        assert repo.search_posts.await_count == 1

    async def test_metrics_increment(self):
        from app.core.metrics import search_cache_hits_total, search_cache_misses_total

        h = search_cache_hits_total.labels(community_id=str(CID))
        m = search_cache_misses_total.labels(community_id=str(CID))
        h0, m0 = h._value.get(), m._value.get()
        svc, _ = _service(FakeRedis())
        user = _user()
        await _search(svc, user)
        await _search(svc, user)
        assert m._value.get() == m0 + 1
        assert h._value.get() == h0 + 1


class TestInvalidation:
    async def test_deletes_only_search_keys(self):
        redis = FakeRedis()
        redis.data = {"search:abc:0": "{}", "search:def:0": "{}", "branding:x": "{}"}
        assert await invalidate_search_cache_for_community(CID, client=redis) == 2
        assert list(redis.data) == ["branding:x"]

    async def test_increments_metric(self):
        from app.core.metrics import search_cache_invalidations_total

        c = search_cache_invalidations_total.labels(community_id=str(CID))
        c0 = c._value.get()
        await invalidate_search_cache_for_community(CID, client=FakeRedis())
        assert c._value.get() == c0 + 1

    async def test_valkey_down_returns_zero(self):
        assert await invalidate_search_cache_for_community(CID, client=BrokenRedis()) == 0


def _inv(module: str):
    """@brief Patch the invalidator as imported by a service module."""
    return patch(f"app.services.{module}.invalidate_search_cache_for_community", new=AsyncMock())


def _post_service():
    from app.services.post_service import PostService

    repo = AsyncMock()
    repo.create_post.return_value = MagicMock(subgroup_id=None)
    repo.get_post_detail.return_value = {"id": "p"}
    return PostService(repo, AsyncMock(), AsyncMock(), AsyncMock(), CID), repo


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
    repo.get_by_id.return_value = MagicMock(owner_id=owner)
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
        inv.assert_awaited_once_with(CID)

    async def test_update_post_invalidates(self):
        svc, repo = _post_service()
        user = _user()
        repo.get_by_id.return_value = MagicMock(author_id=user.id)
        with _inv("post_service") as inv:
            await svc.update_post(uuid.uuid4(), user, "edited")
        inv.assert_awaited_once_with(CID)

    async def test_delete_post_invalidates(self):
        svc, repo = _post_service()
        user = _user()
        repo.get_by_id.return_value = MagicMock(author_id=user.id)
        with _inv("post_service") as inv:
            await svc.delete_post(uuid.uuid4(), user)
        inv.assert_awaited_once_with(CID)

    async def test_create_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        data = MagicMock(recurrence_rule=None, visibility="community", contribution_slots=[])
        with _inv("event_service") as inv:
            await svc.create_event(uid, data)
        inv.assert_awaited_once_with(CID)

    async def test_update_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        data = MagicMock()
        data.model_dump.return_value = {"title": "x"}
        with _inv("event_service") as inv:
            await svc.update_event(uuid.uuid4(), uid, data)
        inv.assert_awaited_once_with(CID)

    async def test_delete_event_invalidates(self):
        uid = uuid.uuid4()
        svc = _event_service(uid)
        with _inv("event_service") as inv:
            await svc.delete_event(uuid.uuid4(), uid)
        inv.assert_awaited_once_with(CID)

    async def test_create_gallery_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        data = MagicMock(visibility="community")
        with _inv("gallery_service") as inv, patch("app.services.gallery_service.GalleryResponse"):
            await svc.create_gallery(uid, data)
        inv.assert_awaited_once_with(CID)

    async def test_update_gallery_invalidates(self):
        uid = uuid.uuid4()
        svc = _gallery_service(uid)
        data = MagicMock()
        data.model_dump.return_value = {"title": "x"}
        with _inv("gallery_service") as inv, patch("app.services.gallery_service.GalleryResponse"):
            await svc.update_gallery(uuid.uuid4(), uid, data)
        inv.assert_awaited_once_with(CID)

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
        inv.assert_awaited_once_with(CID)

    async def test_delete_media_invalidates(self):
        user = _user()
        svc = _media_service(user.id)
        with (
            _inv("media_service") as inv,
            patch("app.services.media_service.decrement_storage_used", new=AsyncMock()),
        ):
            await svc.delete(uuid.uuid4(), user)
        inv.assert_awaited_once_with(CID)


class TestEndToEnd:
    async def test_new_post_invalidates_cached_search(self):
        redis = FakeRedis()
        search, repo = _service(redis)
        user = _user()
        await _search(search, user)
        await _search(search, user)
        assert repo.search_posts.await_count == 1

        async def real_inv(cid):
            return await invalidate_search_cache_for_community(cid, client=redis)

        posts, _ = _post_service()
        with patch("app.services.post_service.invalidate_search_cache_for_community", new=real_inv):
            await posts.create_post(user, "new content")
        assert redis.data == {}

        await _search(search, user)
        assert repo.search_posts.await_count == 2
