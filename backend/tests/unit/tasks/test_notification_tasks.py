"""@file Tests for the send_push_notification task implementation."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.tasks import notification_tasks as nt

PAYLOAD = {"title": "T", "body": "B", "url": "/x"}


def _run(
    subs: list,
    send_side_effect: Exception | None = None,
    community_id: object | None = ...,
) -> tuple[dict, AsyncMock]:
    uid = uuid4()
    session_cm = MagicMock()
    session = MagicMock()
    session.scalar = AsyncMock(return_value=uuid4() if community_id is ... else community_id)
    session.commit = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    repo = MagicMock()
    repo.list_for_user = AsyncMock(return_value=subs)
    service = MagicMock()
    service.send_push = AsyncMock(side_effect=send_side_effect)
    with (
        patch.object(nt, "async_session_factory", return_value=session_cm),
        patch.object(nt, "PushSubscriptionRepository", return_value=repo),
        patch.object(nt, "PushService", return_value=service),
        patch.object(nt, "get_settings", return_value=MagicMock()),
    ):
        result = nt.send_push_notification(str(uid), PAYLOAD)
    return result, service.send_push


def test_sends_when_subscriptions_exist() -> None:
    result, send = _run([MagicMock(), MagicMock()])
    assert result == {"status": "sent", "count": 2}
    send.assert_awaited_once()
    assert send.await_args.args[1:] == ("T", "B", "/x")


def test_skipped_without_subscriptions() -> None:
    result, send = _run([])
    assert result == {"status": "skipped", "count": 0}
    send.assert_not_awaited()


def test_invalid_uuid_skipped() -> None:
    assert nt.send_push_notification("nope", PAYLOAD) == {"status": "skipped", "count": 0}


def test_send_error_is_swallowed() -> None:
    result, _ = _run([MagicMock()], RuntimeError("boom"))
    assert result == {"status": "error", "count": 0}


def test_skipped_when_user_has_no_community() -> None:
    result, send = _run([MagicMock()], community_id=None)
    assert result == {"status": "skipped", "count": 0}
    send.assert_not_awaited()
