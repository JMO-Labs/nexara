"""@file Tests for the Web Push notification channel."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.push import PushChannel

TASK = "app.services.notifications.channels.push.send_push_notification"


def _notif(payload: dict | None = None) -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.type = "new_post"
    n.payload = payload if payload is not None else {"message": "hi", "link": "/p/1"}
    return n


async def test_send_enqueues_task() -> None:
    n = _notif()
    with patch(TASK) as task:
        result = await PushChannel().send(n)
    assert result == ChannelResult(ok=True)
    task.delay.assert_called_once_with(
        str(n.user_id), {"title": "New Post", "body": "hi", "url": "/p/1"}
    )


async def test_send_missing_link_gives_none_url() -> None:
    n = _notif({"message": "hi"})
    with patch(TASK) as task:
        await PushChannel().send(n)
    assert task.delay.call_args.args[1]["url"] is None


async def test_broker_error_returns_failed_result() -> None:
    with patch(TASK) as task:
        task.delay.side_effect = RuntimeError("broker down")
        result = await PushChannel().send(_notif())
    assert result == ChannelResult(ok=False, error="broker down")
