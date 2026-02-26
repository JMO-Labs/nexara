"""
@file test_valkey_integration.py
@brief Integration tests for Valkey connection helpers and cache against a live instance.

Requires a running Valkey/Redis on localhost:6379.
Run with: pytest tests/integration/test_valkey_integration.py -v
"""

import asyncio

import pytest
from redis.asyncio import Redis

from app.core.cache import cache_delete, cache_get, cache_set
from app.core.config import Settings
from app.core.valkey import (
    DB_BROKER,
    DB_CACHE,
    DB_PUBSUB,
    check_valkey_health,
    create_pool,
)

TEST_SETTINGS = Settings(
    SECRET_KEY="integration-test",
    REDIS_URL="redis://localhost:6379",
)

TEST_KEY_PREFIX = "nexara:test:"
"""@brief All test keys use this prefix to avoid collision with real data."""


@pytest.fixture
def broker_client() -> Redis:
    """@brief Create a fresh Redis client for DB 0 (broker)."""
    return create_pool(TEST_SETTINGS, db=DB_BROKER)


@pytest.fixture
def pubsub_client() -> Redis:
    """@brief Create a fresh Redis client for DB 1 (pub/sub)."""
    return create_pool(TEST_SETTINGS, db=DB_PUBSUB)


@pytest.fixture
def cache_client() -> Redis:
    """@brief Create a fresh Redis client for DB 2 (cache)."""
    return create_pool(TEST_SETTINGS, db=DB_CACHE)


@pytest.fixture(autouse=True)
async def cleanup_test_keys(broker_client: Redis, cache_client: Redis, pubsub_client: Redis):
    """@brief Remove any test keys before and after each test."""
    clients = [broker_client, cache_client, pubsub_client]
    yield
    for client in clients:
        keys = await client.keys(f"{TEST_KEY_PREFIX}*")
        if keys:
            await client.delete(*keys)
        await client.aclose()


class TestValkeyHealthCheckIntegration:
    """@brief Verify health check against a real Valkey instance."""

    async def test_ping_succeeds(self, cache_client: Redis):
        result = await check_valkey_health(cache_client)
        assert result is True

    async def test_ping_fails_on_bad_host(self):
        bad_settings = Settings(
            SECRET_KEY="test",
            REDIS_URL="redis://192.0.2.1:6379",
        )
        bad_client = create_pool(bad_settings, db=0, socket_connect_timeout=1.0, socket_timeout=1.0)
        result = await check_valkey_health(bad_client)
        assert result is False
        await bad_client.aclose()


class TestDatabaseIsolation:
    """@brief Verify that logical databases are isolated from each other."""

    async def test_write_to_db0_not_visible_in_db2(
        self, broker_client: Redis, cache_client: Redis
    ):
        key = f"{TEST_KEY_PREFIX}isolation"
        await broker_client.set(key, "broker-value")

        result = await cache_client.get(key)
        assert result is None

        await broker_client.delete(key)

    async def test_write_to_db2_not_visible_in_db1(
        self, cache_client: Redis, pubsub_client: Redis
    ):
        key = f"{TEST_KEY_PREFIX}isolation2"
        await cache_client.set(key, "cache-value")

        result = await pubsub_client.get(key)
        assert result is None

        await cache_client.delete(key)


class TestCacheIntegration:
    """@brief Verify cache_get / cache_set / cache_delete against a live Valkey."""

    async def test_roundtrip(self, cache_client: Redis):
        key = f"{TEST_KEY_PREFIX}roundtrip"
        await cache_set(cache_client, key, '{"name": "alice"}', ttl=60)

        result = await cache_get(cache_client, key)
        assert result == '{"name": "alice"}'

    async def test_cache_miss_returns_none(self, cache_client: Redis):
        result = await cache_get(cache_client, f"{TEST_KEY_PREFIX}nonexistent")
        assert result is None

    async def test_cache_delete_removes_key(self, cache_client: Redis):
        key = f"{TEST_KEY_PREFIX}to-delete"
        await cache_set(cache_client, key, "temporary", ttl=60)
        assert await cache_get(cache_client, key) == "temporary"

        deleted = await cache_delete(cache_client, key)
        assert deleted is True
        assert await cache_get(cache_client, key) is None

    async def test_ttl_expiry(self, cache_client: Redis):
        """@brief Verify that keys expire after their TTL elapses."""
        key = f"{TEST_KEY_PREFIX}ttl-test"
        await cache_set(cache_client, key, "short-lived", ttl=1)

        result = await cache_get(cache_client, key)
        assert result == "short-lived"

        await asyncio.sleep(2)

        result = await cache_get(cache_client, key)
        assert result is None
