"""
@file test_cache.py
@brief TDD unit tests for the fault-tolerant cache helpers.

All tests use a mocked Redis client to verify correct behaviour
without requiring a running Valkey instance.
"""

import uuid
from unittest.mock import AsyncMock

from app.core.cache import DEFAULT_TTL, cache_delete, cache_get, cache_set


class TestCacheGet:
    """@brief Verify cache_get behaviour and fault tolerance."""

    async def test_returns_cached_value(self):
        client = AsyncMock()
        client.get.return_value = '{"name": "alice"}'

        result = await cache_get(client, "user:1:profile")
        assert result == '{"name": "alice"}'
        client.get.assert_called_once_with("user:1:profile")

    async def test_returns_none_on_miss(self):
        client = AsyncMock()
        client.get.return_value = None

        result = await cache_get(client, "nonexistent")
        assert result is None

    async def test_returns_none_on_connection_error(self):
        """@brief Fault tolerance: connection errors yield None, not an exception."""
        client = AsyncMock()
        client.get.side_effect = ConnectionError("Valkey unavailable")

        result = await cache_get(client, "user:1:profile")
        assert result is None

    async def test_returns_none_on_timeout(self):

        client = AsyncMock()
        client.get.side_effect = TimeoutError()

        result = await cache_get(client, "user:1:profile")
        assert result is None


class TestCacheSet:
    """@brief Verify cache_set behaviour and fault tolerance."""

    async def test_stores_value_with_default_ttl(self):
        client = AsyncMock()
        client.setex.return_value = True

        result = await cache_set(client, "user:1:profile", '{"name": "alice"}')
        assert result is True
        client.setex.assert_called_once_with("user:1:profile", DEFAULT_TTL, '{"name": "alice"}')

    async def test_stores_value_with_custom_ttl(self):
        client = AsyncMock()
        client.setex.return_value = True

        result = await cache_set(client, "event:5:attendees", "42", ttl=120)
        assert result is True
        client.setex.assert_called_once_with("event:5:attendees", 120, "42")

    async def test_returns_false_on_connection_error(self):
        """@brief Fault tolerance: write failures are silently absorbed."""
        client = AsyncMock()
        client.setex.side_effect = ConnectionError("Valkey unavailable")

        result = await cache_set(client, "user:1:profile", '{"name": "alice"}')
        assert result is False

    async def test_returns_false_on_timeout(self):

        client = AsyncMock()
        client.setex.side_effect = TimeoutError()

        result = await cache_set(client, "user:1:profile", '{"name": "alice"}')
        assert result is False


class TestCacheDelete:
    """@brief Verify cache_delete behaviour and fault tolerance."""

    async def test_deletes_key(self):
        client = AsyncMock()
        client.delete.return_value = 1

        result = await cache_delete(client, "user:1:profile")
        assert result is True
        client.delete.assert_called_once_with("user:1:profile")

    async def test_returns_true_when_key_missing(self):
        """@brief Deleting a nonexistent key is not an error."""
        client = AsyncMock()
        client.delete.return_value = 0

        result = await cache_delete(client, "nonexistent")
        assert result is True

    async def test_returns_false_on_connection_error(self):
        """@brief Fault tolerance: delete failures are silently absorbed."""
        client = AsyncMock()
        client.delete.side_effect = ConnectionError("Valkey unavailable")

        result = await cache_delete(client, "user:1:profile")
        assert result is False

    async def test_returns_false_on_timeout(self):

        client = AsyncMock()
        client.delete.side_effect = TimeoutError()

        result = await cache_delete(client, "user:1:profile")
        assert result is False


class TestCacheModuleExports:
    """@brief Verify module-level constants are exposed."""

    def test_default_ttl_is_300(self):
        assert DEFAULT_TTL == 300


class TestInvalidateSearchCache:
    """@brief SCAN-based search cache invalidation."""

    async def test_default_client_pool_and_multi_page_scan(self):
        from unittest.mock import MagicMock, patch

        from app.core.cache import invalidate_search_cache_for_community

        client = AsyncMock()
        client.scan.side_effect = [(7, ["search:a:0"]), (0, ["search:b:0", "search:c:0"])]
        with (
            patch("app.core.config.get_settings", return_value=MagicMock()),
            patch("app.core.valkey.get_pool", return_value=client) as pool,
        ):
            deleted = await invalidate_search_cache_for_community(uuid.uuid4())
        pool.assert_called_once()
        assert deleted == 3
        assert client.delete.await_count == 2

    async def test_errors_return_zero(self):
        from app.core.cache import invalidate_search_cache_for_community

        client = AsyncMock()
        client.scan.side_effect = ConnectionError("down")
        assert await invalidate_search_cache_for_community(uuid.uuid4(), client) == 0
