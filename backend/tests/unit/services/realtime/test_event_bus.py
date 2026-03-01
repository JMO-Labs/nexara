"""
@file test_event_bus.py
@brief Unit tests for EventBus routing logic.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import (
    CommunityTarget,
    EventType,
    RealtimeEvent,
    UserTarget,
)


@pytest.fixture
def bus():
    """@brief Fresh EventBus instance."""
    return EventBus()


class TestEmitRouting:
    """@brief Verify that emit() routes to the correct publish function."""

    @pytest.mark.asyncio
    @patch("app.services.realtime.pubsub.publish_to_user", new_callable=AsyncMock)
    async def test_emit_user_target(self, mock_publish, bus):
        """emit() routes UserTarget events to publish_to_user."""
        uid = uuid.uuid4()
        event = RealtimeEvent(
            type=EventType.NOTIFICATION,
            target=UserTarget(user_id=uid),
            payload={"message": "hello"},
        )
        mock_publish.return_value = 1

        result = await bus.emit(event)

        assert result == 1
        mock_publish.assert_awaited_once_with(
            uid,
            {"type": "notification", "payload": {"message": "hello"}},
        )

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish_to_community",
        new_callable=AsyncMock,
    )
    async def test_emit_community_target(self, mock_publish, bus):
        """emit() routes CommunityTarget events to publish_to_community."""
        cid = uuid.uuid4()
        event = RealtimeEvent(
            type=EventType.FEED_UPDATE,
            target=CommunityTarget(community_id=cid),
            payload={"event": "created", "post": {}},
        )
        mock_publish.return_value = 3

        result = await bus.emit(event)

        assert result == 3
        mock_publish.assert_awaited_once_with(
            cid,
            {"type": "feed_update", "payload": {"event": "created", "post": {}}},
        )

    @pytest.mark.asyncio
    async def test_emit_unknown_target_returns_zero(self, bus):
        """emit() returns 0 for unrecognised target types."""
        from app.services.realtime.events import EventTarget

        event = RealtimeEvent(
            type=EventType.PRESENCE,
            target=EventTarget(),
            payload={"status": "online"},
        )
        result = await bus.emit(event)
        assert result == 0
