"""
@file test_connection_manager.py
@brief Unit tests for the ConnectionManager: connect, disconnect, send_to_user, broadcast.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.realtime.connection_manager import ConnectionManager


@pytest.fixture
def manager():
    """@brief Fresh ConnectionManager for each test."""
    return ConnectionManager()


def _mock_conn():
    """@brief Create a mock Sendable with an async send_json."""
    conn = AsyncMock()
    conn.send_json = AsyncMock()
    return conn


class TestConnect:
    """@brief Verify connection registration."""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self, manager):
        conn = _mock_conn()
        uid = uuid.uuid4()

        await manager.connect(conn, uid)

        assert uid in manager.connected_user_ids
        assert manager.total_connections == 1

    @pytest.mark.asyncio
    async def test_connect_multiple_per_user(self, manager):
        uid = uuid.uuid4()
        await manager.connect(_mock_conn(), uid)
        await manager.connect(_mock_conn(), uid)

        assert manager.total_connections == 2

    @pytest.mark.asyncio
    async def test_connect_ws_increments_gauge(self, manager):
        await manager.connect(_mock_conn(), uuid.uuid4(), is_sse=False)
        assert manager._ws_count == 1
        assert manager._sse_count == 0

    @pytest.mark.asyncio
    async def test_connect_sse_increments_gauge(self, manager):
        await manager.connect(_mock_conn(), uuid.uuid4(), is_sse=True)
        assert manager._sse_count == 1
        assert manager._ws_count == 0


class TestDisconnect:
    """@brief Verify connection removal."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        conn = _mock_conn()
        uid = uuid.uuid4()
        await manager.connect(conn, uid)
        await manager.disconnect(conn, uid)

        assert uid not in manager.connected_user_ids
        assert manager.total_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_is_safe(self, manager):
        await manager.disconnect(_mock_conn(), uuid.uuid4())
        assert manager.total_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_one_of_many(self, manager):
        uid = uuid.uuid4()
        c1, c2 = _mock_conn(), _mock_conn()
        await manager.connect(c1, uid)
        await manager.connect(c2, uid)
        await manager.disconnect(c1, uid)

        assert manager.total_connections == 1
        assert uid in manager.connected_user_ids


class TestSendToUser:
    """@brief Verify targeted message delivery."""

    @pytest.mark.asyncio
    async def test_send_delivers_to_all_connections(self, manager):
        uid = uuid.uuid4()
        c1, c2 = _mock_conn(), _mock_conn()
        await manager.connect(c1, uid)
        await manager.connect(c2, uid)

        sent = await manager.send_to_user(uid, {"type": "test"})

        assert sent == 2
        c1.send_json.assert_called_once_with({"type": "test"})
        c2.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_offline_user_returns_zero(self, manager):
        sent = await manager.send_to_user(uuid.uuid4(), {"type": "test"})
        assert sent == 0

    @pytest.mark.asyncio
    async def test_send_handles_failing_connection(self, manager):
        uid = uuid.uuid4()
        good = _mock_conn()
        bad = _mock_conn()
        bad.send_json.side_effect = RuntimeError("Connection lost")

        await manager.connect(good, uid)
        await manager.connect(bad, uid)

        sent = await manager.send_to_user(uid, {"type": "test"})
        assert sent == 1
        good.send_json.assert_called_once()


class TestSendToCommunity:
    """@brief Verify community-scoped message delivery."""

    @pytest.mark.asyncio
    async def test_send_to_community_reaches_members(self, manager):
        cid = uuid.uuid4()
        c1, c2 = _mock_conn(), _mock_conn()
        uid1, uid2 = uuid.uuid4(), uuid.uuid4()
        await manager.connect(c1, uid1, community_id=cid)
        await manager.connect(c2, uid2, community_id=cid)

        sent = await manager.send_to_community(cid, {"type": "feed_update"})

        assert sent == 2
        c1.send_json.assert_called_once()
        c2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_community_excludes_other_communities(self, manager):
        cid_a, cid_b = uuid.uuid4(), uuid.uuid4()
        c_a, c_b = _mock_conn(), _mock_conn()
        await manager.connect(c_a, uuid.uuid4(), community_id=cid_a)
        await manager.connect(c_b, uuid.uuid4(), community_id=cid_b)

        sent = await manager.send_to_community(cid_a, {"type": "test"})

        assert sent == 1
        c_a.send_json.assert_called_once()
        c_b.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_community_includes_unscoped_users(self, manager):
        """Users connected without community_id receive all community messages."""
        cid = uuid.uuid4()
        c_scoped = _mock_conn()
        c_unscoped = _mock_conn()
        await manager.connect(c_scoped, uuid.uuid4(), community_id=cid)
        await manager.connect(c_unscoped, uuid.uuid4())

        sent = await manager.send_to_community(cid, {"type": "test"})

        assert sent == 2
        c_scoped.send_json.assert_called_once()
        c_unscoped.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_community_mapping(self, manager):
        cid = uuid.uuid4()
        uid = uuid.uuid4()
        conn = _mock_conn()
        await manager.connect(conn, uid, community_id=cid)
        await manager.disconnect(conn, uid)

        assert uid not in manager._user_community

    @pytest.mark.asyncio
    async def test_send_to_community_empty(self, manager):
        sent = await manager.send_to_community(uuid.uuid4(), {"type": "test"})
        assert sent == 0


class TestBroadcast:
    """@brief Verify broadcast to all connected users."""

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all(self, manager):
        c1, c2 = _mock_conn(), _mock_conn()
        await manager.connect(c1, uuid.uuid4())
        await manager.connect(c2, uuid.uuid4())

        sent = await manager.broadcast({"type": "announcement"})

        assert sent == 2
        c1.send_json.assert_called_once()
        c2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_empty_manager(self, manager):
        sent = await manager.broadcast({"type": "test"})
        assert sent == 0
