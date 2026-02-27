"""
@file test_valkey.py
@brief TDD unit tests for the Valkey connection helper module.

Tests verify connection pool creation, DB index routing, health check logic,
pool lifecycle management, and graceful degradation.
"""

from unittest.mock import AsyncMock

from app.core.config import Settings


class TestValkeyURLGeneration:
    """@brief Verify URL construction for each logical DB."""

    def test_broker_pool_uses_db_0(self):
        from app.core.valkey import get_valkey_url

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://valkey:6379")
        assert get_valkey_url(settings, db=0) == "redis://valkey:6379/0"

    def test_pubsub_pool_uses_db_1(self):
        from app.core.valkey import get_valkey_url

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://valkey:6379")
        assert get_valkey_url(settings, db=1) == "redis://valkey:6379/1"

    def test_cache_pool_uses_db_2(self):
        from app.core.valkey import get_valkey_url

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://valkey:6379")
        assert get_valkey_url(settings, db=2) == "redis://valkey:6379/2"

    def test_url_with_password(self):
        from app.core.valkey import get_valkey_url

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://:secret@valkey:6379")
        assert get_valkey_url(settings, db=0) == "redis://:secret@valkey:6379/0"

    def test_url_strips_trailing_slash(self):
        from app.core.valkey import get_valkey_url

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://valkey:6379/")
        assert get_valkey_url(settings, db=2) == "redis://valkey:6379/2"


class TestValkeyPoolCreation:
    """@brief Verify pool objects are created with correct parameters."""

    def test_create_pool_returns_redis_instance(self):
        from app.core.valkey import create_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        pool = create_pool(settings, db=0)
        assert pool is not None
        assert hasattr(pool, "ping")

    def test_create_cache_pool(self):
        from app.core.valkey import create_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        pool = create_pool(settings, db=2)
        assert pool is not None

    def test_pools_are_different_instances(self):
        from app.core.valkey import create_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        broker = create_pool(settings, db=0)
        cache = create_pool(settings, db=2)
        assert broker is not cache


class TestValkeyPoolRegistry:
    """@brief Verify the shared pool registry (get_pool / close_pools)."""

    def setup_method(self):
        """@brief Reset the global pool registry before each test."""
        import app.core.valkey as mod

        mod._pools.clear()

    def test_get_pool_creates_on_first_call(self):
        from app.core.valkey import _pools, get_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        pool = get_pool(settings, db=0)
        assert pool is not None
        assert 0 in _pools

    def test_get_pool_returns_same_instance(self):
        from app.core.valkey import get_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        first = get_pool(settings, db=1)
        second = get_pool(settings, db=1)
        assert first is second

    def test_get_pool_different_dbs_different_instances(self):
        from app.core.valkey import get_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        broker = get_pool(settings, db=0)
        cache = get_pool(settings, db=2)
        assert broker is not cache

    async def test_close_pools_clears_registry(self):
        from app.core.valkey import _pools, close_pools, get_pool

        settings = Settings(SECRET_KEY="test", REDIS_URL="redis://localhost:6379")
        get_pool(settings, db=0)
        get_pool(settings, db=2)
        assert len(_pools) == 2

        await close_pools()
        assert len(_pools) == 0

    async def test_close_pools_handles_errors_gracefully(self):
        """@brief close_pools should not raise even if aclose fails."""
        from app.core.valkey import _pools, close_pools

        mock_pool = AsyncMock()
        mock_pool.aclose.side_effect = ConnectionError("already closed")
        _pools[99] = mock_pool

        await close_pools()
        assert len(_pools) == 0


class TestValkeyHealthCheck:
    """@brief Verify the health check reports Valkey status correctly."""

    async def test_healthy_returns_true(self):
        from app.core.valkey import check_valkey_health

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        result = await check_valkey_health(mock_redis)
        assert result is True
        mock_redis.ping.assert_called_once()

    async def test_unhealthy_returns_false(self):
        from app.core.valkey import check_valkey_health

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Connection refused")

        result = await check_valkey_health(mock_redis)
        assert result is False

    async def test_timeout_returns_false(self):
        from app.core.valkey import check_valkey_health

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = TimeoutError()

        result = await check_valkey_health(mock_redis)
        assert result is False


class TestValkeyModuleExports:
    """@brief Verify the module exposes the expected public API."""

    def test_module_exports_create_pool(self):
        from app.core import valkey
        assert hasattr(valkey, "create_pool")

    def test_module_exports_get_pool(self):
        from app.core import valkey
        assert hasattr(valkey, "get_pool")

    def test_module_exports_close_pools(self):
        from app.core import valkey
        assert hasattr(valkey, "close_pools")

    def test_module_exports_check_health(self):
        from app.core import valkey
        assert hasattr(valkey, "check_valkey_health")

    def test_module_exports_get_url(self):
        from app.core import valkey
        assert hasattr(valkey, "get_valkey_url")

    def test_module_exports_db_constants(self):
        from app.core.valkey import DB_BROKER, DB_CACHE, DB_PUBSUB
        assert DB_BROKER == 0
        assert DB_PUBSUB == 1
        assert DB_CACHE == 2
