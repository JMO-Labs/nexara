"""@file Tests for the Apprise channel, URL encryption and apprise_deliver task."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.models.apprise_url import AppriseURL
from app.models.notification import Notification
from app.repositories.apprise_repo import AppriseRepository
from app.services.notifications.channels.apprise import AppriseChannel
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.dispatcher import Dispatcher
from app.services.notifications.secrets import decrypt_url, encrypt_url

CH = "app.services.notifications.channels.apprise"
TASKS = "app.tasks.notification_tasks"


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPRISE_ENCRYPTION_KEY", Fernet.generate_key().decode())


def _factory(repo: AsyncMock):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def _cm():  # type: ignore[no-untyped-def]
        yield repo

    return _cm


def _notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = uuid4()
    n.user_id = uuid4()
    n.community_id = uuid4()
    n.type = "new_post"
    n.payload = {"message": "hi"}
    return n


def _row(enabled: bool = True) -> MagicMock:
    r = MagicMock(spec=AppriseURL)
    r.id = uuid4()
    r.enabled = enabled
    return r


def test_encrypt_roundtrip_and_not_plaintext() -> None:
    token = encrypt_url("discord://id/token")
    assert "discord" not in token
    assert decrypt_url(token) == "discord://id/token"


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPRISE_ENCRYPTION_KEY")
    with pytest.raises(RuntimeError):
        encrypt_url("x://y")


async def test_channel_fans_out_to_enabled_urls() -> None:
    repo = AsyncMock(spec=AppriseRepository)
    rows = [_row(), _row()]
    repo.list_for_user.return_value = rows
    n = _notif()
    with patch(f"{CH}.apprise_deliver") as task:
        res = await AppriseChannel(_factory(repo)).send(n)
    assert res == ChannelResult(ok=True)
    assert task.delay.call_count == 2
    task.delay.assert_any_call(str(rows[0].id), str(n.id), "New Post", "hi")


async def test_channel_skips_without_urls() -> None:
    repo = AsyncMock(spec=AppriseRepository)
    repo.list_for_user.return_value = []
    res = await AppriseChannel(_factory(repo)).send(_notif())
    assert res.ok and res.skipped_reason == "no_urls"


async def test_channel_never_raises() -> None:
    repo = AsyncMock(spec=AppriseRepository)
    repo.list_for_user.side_effect = RuntimeError("db down")
    res = await AppriseChannel(_factory(repo)).send(_notif())
    assert res == ChannelResult(ok=False, error="db down")


async def test_dispatcher_registers_apprise() -> None:
    assert "apprise" in Dispatcher(MagicMock())._channels


def _run_task(status: int | None, ok: bool, failures: int = 0) -> tuple[MagicMock, MagicMock]:
    repo = AsyncMock(spec=AppriseRepository)
    row = _row()
    row.apprise_url = "discord://a/b"
    repo.get.return_value = row
    repo.record_failure.return_value = failures
    apobj = MagicMock()
    apobj.notify.return_value = ok
    return repo, apobj


async def test_deliver_success_records_success() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    repo, apobj = _run_task(None, True)
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj):
        out = await _apprise_deliver_async(repo, uuid4(), "T", "B")
    assert out == "sent"
    apobj.add.assert_called_once_with("discord://a/b")
    repo.record_success.assert_awaited_once()


async def test_deliver_failure_increments_and_does_not_retry() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    repo, apobj = _run_task(None, False)
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj):
        out = await _apprise_deliver_async(repo, uuid4(), "T", "B")
    assert out == "failed"
    repo.record_failure.assert_awaited_once()


async def test_deliver_transient_raises_for_retry() -> None:
    from app.tasks.notification_tasks import TransientDeliveryError, _apprise_deliver_async

    repo, apobj = _run_task(None, False)
    apobj.notify.side_effect = TimeoutError("slow")
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj), pytest.raises(
        TransientDeliveryError
    ):
        await _apprise_deliver_async(repo, uuid4(), "T", "B")
    repo.record_failure.assert_not_awaited()
