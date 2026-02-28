"""
@file test_presence.py
@brief Unit tests for the presence tracking module with mocked Valkey.
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.realtime.presence import (
    PRESENCE_KEY,
    PRESENCE_TTL_SECONDS,
    cleanup_stale,
    get_online_count,
    get_online_users,
    is_online,
    set_offline,
    set_online,
)


@pytest.fixture
def mock_pool():
    """@brief Patch get_pool to return a mocked async Redis client."""
    pool = AsyncMock()
    with patch("app.services.realtime.presence.get_pool", return_value=pool):
        yield pool


class TestSetOnline:
    """@brief Verify set_online adds to sorted set."""

    @pytest.mark.asyncio
    async def test_calls_zadd(self, mock_pool):
        uid = uuid.uuid4()
        await set_online(uid)

        mock_pool.zadd.assert_called_once()
        call_args = mock_pool.zadd.call_args
        assert call_args[0][0] == PRESENCE_KEY
        member_dict = call_args[0][1]
        assert str(uid) in member_dict


class TestSetOffline:
    """@brief Verify set_offline removes from sorted set."""

    @pytest.mark.asyncio
    async def test_calls_zrem(self, mock_pool):
        uid = uuid.uuid4()
        await set_offline(uid)

        mock_pool.zrem.assert_called_once_with(PRESENCE_KEY, str(uid))


class TestGetOnlineUsers:
    """@brief Verify get_online_users queries with TTL window."""

    @pytest.mark.asyncio
    async def test_returns_recent_users(self, mock_pool):
        mock_pool.zrangebyscore.return_value = [b"user-1", b"user-2"]

        result = await get_online_users()

        assert result == ["user-1", "user-2"]
        call_args = mock_pool.zrangebyscore.call_args[0]
        assert call_args[0] == PRESENCE_KEY
        cutoff = call_args[1]
        assert cutoff <= time.time() - PRESENCE_TTL_SECONDS + 1

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, mock_pool):
        mock_pool.zrangebyscore.return_value = []
        result = await get_online_users()
        assert result == []


class TestGetOnlineCount:
    """@brief Verify get_online_count uses ZCOUNT."""

    @pytest.mark.asyncio
    async def test_returns_count(self, mock_pool):
        mock_pool.zcount.return_value = 42
        result = await get_online_count()
        assert result == 42


class TestIsOnline:
    """@brief Verify is_online checks score against TTL."""

    @pytest.mark.asyncio
    async def test_online_user(self, mock_pool):
        mock_pool.zscore.return_value = time.time()
        assert await is_online(uuid.uuid4()) is True

    @pytest.mark.asyncio
    async def test_offline_user(self, mock_pool):
        mock_pool.zscore.return_value = None
        assert await is_online(uuid.uuid4()) is False

    @pytest.mark.asyncio
    async def test_stale_user(self, mock_pool):
        mock_pool.zscore.return_value = time.time() - PRESENCE_TTL_SECONDS - 60
        assert await is_online(uuid.uuid4()) is False


class TestCleanupStale:
    """@brief Verify cleanup_stale removes old entries."""

    @pytest.mark.asyncio
    async def test_removes_stale(self, mock_pool):
        mock_pool.zremrangebyscore.return_value = 3
        mock_pool.zcount.return_value = 10

        removed = await cleanup_stale()

        assert removed == 3
        mock_pool.zremrangebyscore.assert_called_once()
