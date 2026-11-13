"""@file Tests for the in-app SSE notification channel."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.inapp import InAppChannel
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import EventType, UserTarget

ACTOR = uuid4()


def _notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.type = "mention"
    n.payload = {"message": "hi"}
    n.created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    n.updated_at = datetime(2026, 1, 2, 3, 9, 0, tzinfo=UTC)
    n.count = 2
    n.actor_ids = [ACTOR]
    return n


async def test_send_emits_event() -> None:
    bus = AsyncMock(spec=EventBus)
    n = _notif()
    result = await InAppChannel(bus).send(n)
    assert result == ChannelResult(ok=True)
    event = bus.emit.await_args.args[0]
    assert event.type == EventType.NOTIFICATION
    assert isinstance(event.target, UserTarget)
    assert event.target.user_id == n.user_id
    assert event.payload == {
        "id": str(n.id),
        "type": "mention",
        "payload": {"message": "hi"},
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
        "count": 2,
        "actor_ids": [str(ACTOR)],
    }


async def test_send_swallows_errors() -> None:
    bus = AsyncMock(spec=EventBus)
    bus.emit.side_effect = RuntimeError("boom")
    result = await InAppChannel(bus).send(_notif())
    assert result.ok is False
    assert result.error == "boom"


def test_key() -> None:
    assert InAppChannel.key == "inapp"
