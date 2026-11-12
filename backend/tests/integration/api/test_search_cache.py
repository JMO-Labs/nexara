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


class TestInvocationPoints:
    """@brief Mutating service methods trigger invalidation."""

    def test_services_import_invalidator(self):
        import app.services.event_service as e
        import app.services.gallery_service as g
        import app.services.media_service as m
        import app.services.post_service as p

        for mod in (e, g, m, p):
            assert hasattr(mod, "invalidate_search_cache_for_community")

    async def test_delete_post_invalidates(self):
        from app.services.post_service import PostService

        post = MagicMock(author_id=uuid.uuid4())
        user = MagicMock(id=post.author_id, role="member")
        svc = PostService.__new__(PostService)
        svc._post_repo = AsyncMock()
        svc._post_repo.get_by_id.return_value = post
        svc._community_id = CID
        svc._activity_repo = None
        with patch(
            "app.services.post_service.invalidate_search_cache_for_community",
            new=AsyncMock(),
        ) as inv:
            await svc.delete_post(uuid.uuid4(), user)
        inv.assert_awaited_once_with(CID)
