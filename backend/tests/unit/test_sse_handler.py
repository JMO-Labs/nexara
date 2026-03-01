"""
@file test_sse_handler.py
@brief Unit tests for the SSE notification stream endpoint handler.

Tests cover event generation, heartbeat behavior, and connection lifecycle.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.sse import HEARTBEAT_INTERVAL_SECONDS, _event_generator
from app.services.realtime.connection_manager import SSEConnection


class TestEventGenerator:
    """@brief SSE event generator behavior tests."""

    @pytest.mark.asyncio
    async def test_yields_heartbeat_on_timeout(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)

        with (
            patch("app.api.v1.sse.manager") as mock_manager,
            patch("app.api.v1.sse.set_online", new_callable=AsyncMock),
            patch("app.api.v1.sse.set_offline", new_callable=AsyncMock),
        ):
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()

            gen = _event_generator(conn, user_id, None)
            heartbeat_received = False

            with patch("app.api.v1.sse.HEARTBEAT_INTERVAL_SECONDS", 0.01):
                count = 0
                async for event in gen:
                    count += 1
                    if ": heartbeat" in event:
                        heartbeat_received = True
                        break
                    if count > 5:
                        break

            assert heartbeat_received

    @pytest.mark.asyncio
    async def test_yields_initial_connected_event(self):
        """@brief The generator yields a padding flush then a connected event first."""
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)

        with (
            patch("app.api.v1.sse.manager") as mock_manager,
            patch("app.api.v1.sse.set_online", new_callable=AsyncMock),
            patch("app.api.v1.sse.set_offline", new_callable=AsyncMock),
        ):
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()

            gen = _event_generator(conn, user_id, None)
            flush = await gen.__anext__()
            connected = await gen.__anext__()

        assert "retry:" in flush
        assert "event: connected" in connected
        assert str(user_id) in connected

    @pytest.mark.asyncio
    async def test_yields_message_from_queue(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)
        await conn.queue.put({"type": "notification", "payload": {"text": "hello"}})

        with (
            patch("app.api.v1.sse.manager") as mock_manager,
            patch("app.api.v1.sse.set_online", new_callable=AsyncMock),
            patch("app.api.v1.sse.set_offline", new_callable=AsyncMock),
        ):
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()

            gen = _event_generator(conn, user_id, None)
            await gen.__anext__()  # padding flush
            await gen.__anext__()  # connected event
            event = await gen.__anext__()

        assert "event: notification" in event
        assert "hello" in event

    @pytest.mark.asyncio
    async def test_includes_event_id(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)
        await conn.queue.put({"type": "feed_update", "payload": {"post_id": "abc"}})

        with (
            patch("app.api.v1.sse.manager") as mock_manager,
            patch("app.api.v1.sse.set_online", new_callable=AsyncMock),
            patch("app.api.v1.sse.set_offline", new_callable=AsyncMock),
        ):
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()

            gen = _event_generator(conn, user_id, None)
            await gen.__anext__()  # padding flush
            await gen.__anext__()  # connected event
            event = await gen.__anext__()

        assert "id: 1" in event

    @pytest.mark.asyncio
    async def test_logs_reconnect_with_last_event_id(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)

        with (
            patch("app.api.v1.sse.manager") as mock_manager,
            patch("app.api.v1.sse.set_online", new_callable=AsyncMock),
            patch("app.api.v1.sse.set_offline", new_callable=AsyncMock),
            patch("app.api.v1.sse.logger") as mock_logger,
            patch("app.api.v1.sse.HEARTBEAT_INTERVAL_SECONDS", 0.01),
        ):
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()

            gen = _event_generator(conn, user_id, "42")
            count = 0
            async for event in gen:
                count += 1
                if count >= 1:
                    break

            mock_logger.info.assert_any_call(
                "sse_reconnect",
                user_id=str(user_id),
                last_event_id="42",
            )


class TestSSEConnectionWrapper:
    """@brief SSEConnection queue-based wrapper tests."""

    def test_has_queue(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)
        assert hasattr(conn, "queue")
        assert conn.queue.empty()

    @pytest.mark.asyncio
    async def test_send_json_puts_to_queue(self):
        user_id = uuid.uuid4()
        conn = SSEConnection(user_id)
        await conn.send_json({"type": "test"})
        assert not conn.queue.empty()
        msg = await conn.queue.get()
        assert msg == {"type": "test"}


class TestHeartbeatInterval:
    """@brief Heartbeat interval constant tests."""

    def test_interval_is_15_seconds(self):
        assert HEARTBEAT_INTERVAL_SECONDS == 15
