"""
@file test_presence_lifecycle.py
@brief Heartbeat refresh + last-connection-only offline for SSE presence.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.sse import _event_generator
from app.services.realtime.connection_manager import ConnectionManager, SSEConnection


async def test_has_connections_after_disconnect() -> None:
    m = ConnectionManager()
    uid = uuid.uuid4()
    a, b = SSEConnection(uid), SSEConnection(uid)
    await m.connect(a, uid, is_sse=True)
    await m.connect(b, uid, is_sse=True)
    await m.disconnect(a, uid, is_sse=True)
    assert m.has_connections(uid)
    await m.disconnect(b, uid, is_sse=True)
    assert not m.has_connections(uid)


@pytest.mark.parametrize("still_connected", [True, False])
async def test_sse_heartbeat_refreshes_and_offline_only_when_last(still_connected: bool) -> None:
    uid = uuid.uuid4()
    with (
        patch("app.api.v1.sse.manager") as mgr,
        patch("app.api.v1.sse.set_online", new_callable=AsyncMock) as on,
        patch("app.api.v1.sse.set_offline", new_callable=AsyncMock) as off,
        patch("app.api.v1.sse.HEARTBEAT_INTERVAL_SECONDS", 0.01),
    ):
        mgr.connect = AsyncMock()
        mgr.disconnect = AsyncMock()
        mgr.has_connections.return_value = still_connected
        gen = _event_generator(SSEConnection(uid), uid, None)
        async for ev in gen:
            if ": heartbeat" in ev:
                break
        assert on.await_count >= 2  # connect + heartbeat refresh
        await gen.aclose()
        assert off.await_count == (0 if still_connected else 1)
