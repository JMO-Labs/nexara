"""@file Tests for the FCM notification channel."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.channels.fcm import FCMChannel, FCMTokenInvalid


def _notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.community_id = uuid4()
    n.type = "new_post"
    n.payload = {"message": "hi", "link": "/p/1"}
    return n


def _dev(token: str) -> MagicMock:
    d = MagicMock(spec=DeviceToken)
    d.token = token
    return d


class FakeClient:
    def __init__(self, invalid: set[str] | None = None) -> None:
        self.sent: list[tuple[str, dict[str, str]]] = []
        self.invalid = invalid or set()

    async def send(self, token: str, title: str, body: str, data: dict[str, str]) -> None:
        if token in self.invalid:
            raise FCMTokenInvalid(token)
        self.sent.append((token, {"title": title, "body": body, **data}))


def _channel(devices: list[MagicMock], client: FakeClient, creds: str | None = "/c.json"):
    repo = AsyncMock()
    repo.list_active_for_user.return_value = devices
    return FCMChannel(client=client, repo=repo, credentials_file=creds), repo


async def test_sends_once_per_token() -> None:
    client = FakeClient()
    ch, _ = _channel([_dev("a"), _dev("b")], client)
    res = await ch.send(_notif())
    assert res == ChannelResult(ok=True)
    assert [t for t, _ in client.sent] == ["a", "b"]
    assert client.sent[0][1]["body"] == "hi"


async def test_invalid_tokens_soft_deleted() -> None:
    client = FakeClient(invalid={"bad"})
    good, bad = _dev("good"), _dev("bad")
    ch, repo = _channel([bad, good], client)
    res = await ch.send(_notif())
    assert res.ok
    repo.soft_delete.assert_awaited_once_with(bad)
    assert [t for t, _ in client.sent] == ["good"]


async def test_unset_credentials_skips() -> None:
    client = FakeClient()
    ch, repo = _channel([_dev("a")], client, creds=None)
    res = await ch.send(_notif())
    assert res.ok is False and res.skipped_reason == "fcm_not_configured"
    assert client.sent == []
    repo.list_active_for_user.assert_not_called()


async def test_no_devices_skips() -> None:
    ch, _ = _channel([], FakeClient())
    res = await ch.send(_notif())
    assert res.skipped_reason == "no_devices"


async def test_other_client_error_returns_failed() -> None:
    client = FakeClient()
    client.send = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]
    ch, _ = _channel([_dev("a")], client)
    res = await ch.send(_notif())
    assert res.ok is False and res.error == "boom"
