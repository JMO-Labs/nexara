"""@file Tests for the email notification channel."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.email import EmailChannel

TASK = "app.services.notifications.channels.email.send_email_notification"


def _notif(actor_ids: list | None = None) -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.type = "mention"
    n.payload = {"message": "hi"}
    if actor_ids is not None:
        n.actor_ids = actor_ids
    return n


async def test_send_enqueues_task() -> None:
    actor = uuid4()
    n = _notif([actor])
    with patch(TASK) as task:
        result = await EmailChannel().send(n)
    assert result == ChannelResult(ok=True)
    task.delay.assert_called_once_with(
        str(n.user_id), "mention", {"message": "hi", "actor_ids": [str(actor)]}
    )


async def test_send_without_actor_ids_defaults_empty() -> None:
    n = _notif()
    with patch(TASK) as task:
        result = await EmailChannel().send(n)
    assert result.ok
    assert task.delay.call_args.args[2]["actor_ids"] == []


async def test_broker_error_returns_failure() -> None:
    with patch(TASK) as task:
        task.delay.side_effect = ConnectionError("broker down")
        result = await EmailChannel().send(_notif())
    assert result == ChannelResult(ok=False, error="broker down")


def test_key() -> None:
    assert EmailChannel.key == "email"
