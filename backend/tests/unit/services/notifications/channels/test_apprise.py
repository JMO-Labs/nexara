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


async def test_effective_channels_route_through_dispatcher_to_apprise() -> None:
    from app.services.notifications import NotificationPayload, NotificationType
    from app.services.notifications.prefs import effective_channels

    t = NotificationType(
        key="new_post",
        category="social",
        payload_schema=NotificationPayload,
        default_channels={"inapp": True},
    )
    d = Dispatcher(MagicMock())
    for k in list(d._channels):
        if k != "apprise":
            d._channels[k] = AsyncMock(send=AsyncMock(return_value=ChannelResult(ok=True)))
    ok = AsyncMock(return_value=ChannelResult(ok=True))
    with patch.object(AppriseChannel, "send", new=ok) as send:
        await d.dispatch(_notif(), t, dict(effective_channels(t, {"new_post": {"apprise": True}})))
    send.assert_awaited_once()


def _run_task(ok: bool, enabled: bool = True) -> tuple[AsyncMock, MagicMock]:
    repo = AsyncMock(spec=AppriseRepository)
    row = _row(enabled)
    row.apprise_url = "discord://a/b"
    repo.get.return_value = row
    repo.record_failure.return_value = 1
    apobj = MagicMock()
    apobj.notify.return_value = ok
    return repo, apobj


async def test_deliver_success_records_success() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    repo, apobj = _run_task(True)
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj):
        out = await _apprise_deliver_async(repo, uuid4(), "T", "B")
    assert out == "sent"
    apobj.add.assert_called_once_with("discord://a/b")
    repo.record_success.assert_awaited_once()


async def test_deliver_failure_increments_and_does_not_retry() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    repo, apobj = _run_task(False)
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj):
        out = await _apprise_deliver_async(repo, uuid4(), "T", "B")
    assert out == "failed"
    repo.record_failure.assert_awaited_once()


async def test_deliver_transient_raises_for_retry() -> None:
    from app.tasks.notification_tasks import TransientDeliveryError, _apprise_deliver_async

    repo, apobj = _run_task(False)
    apobj.notify.side_effect = TimeoutError("slow")
    with (
        patch(f"{TASKS}.apprise.Apprise", return_value=apobj),
        pytest.raises(TransientDeliveryError),
    ):
        await _apprise_deliver_async(repo, uuid4(), "T", "B")
    repo.record_failure.assert_not_awaited()


async def test_deliver_disabled_row_skipped() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    repo, apobj = _run_task(True, enabled=False)
    with patch(f"{TASKS}.apprise.Apprise", return_value=apobj):
        out = await _apprise_deliver_async(repo, uuid4(), "T", "B")
    assert out == "skipped"
    apobj.notify.assert_not_called()


@pytest.mark.parametrize("retries", [0, 2])
def test_task_retries_transient_with_jittered_backoff(retries: int) -> None:
    from app.tasks.notification_tasks import TransientDeliveryError, apprise_deliver

    assert apprise_deliver.max_retries == 5

    class _RetryError(Exception):
        pass

    apprise_deliver.push_request(retries=retries)
    try:
        with (
            patch(
                f"{TASKS}._apprise_deliver_run",
                new=AsyncMock(side_effect=TransientDeliveryError("timeout")),
            ),
            patch.object(apprise_deliver, "retry", side_effect=_RetryError()) as retry,
            pytest.raises(_RetryError),
        ):
            apprise_deliver.run(str(uuid4()), str(uuid4()), "T", "B")
    finally:
        apprise_deliver.pop_request()
    retry.assert_called_once()
    countdown = retry.call_args.kwargs["countdown"]
    assert 0 <= countdown <= 2**retries * 30


async def test_default_repo_yields_repository_on_session() -> None:
    from app.services.notifications.channels.apprise import _default_repo

    session = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch(f"{CH}.async_session_factory", return_value=cm):
        async with _default_repo() as repo:
            assert isinstance(repo, AppriseRepository)
    cm.__aexit__.assert_awaited_once()


async def test_deliver_run_commits_and_returns_status() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_run

    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with (
        patch(f"{TASKS}.async_session_factory", return_value=cm),
        patch(f"{TASKS}._apprise_deliver_async", new=AsyncMock(return_value="sent")),
    ):
        assert await _apprise_deliver_run(uuid4(), "T", "B") == "sent"
    session.commit.assert_awaited_once()


async def test_deliver_run_commits_even_on_error() -> None:
    from app.tasks.notification_tasks import TransientDeliveryError, _apprise_deliver_run

    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with (
        patch(f"{TASKS}.async_session_factory", return_value=cm),
        patch(
            f"{TASKS}._apprise_deliver_async",
            new=AsyncMock(side_effect=TransientDeliveryError("x")),
        ),
        pytest.raises(TransientDeliveryError),
    ):
        await _apprise_deliver_run(uuid4(), "T", "B")
    session.commit.assert_awaited_once()


def test_task_invalid_uuid_is_skipped() -> None:
    from app.tasks.notification_tasks import apprise_deliver

    out = apprise_deliver.run("not-a-uuid", str(uuid4()), "T", "B")
    assert out == {"status": "skipped"}


def test_task_success_returns_status() -> None:
    from app.tasks.notification_tasks import apprise_deliver

    with patch(f"{TASKS}._apprise_deliver_run", new=AsyncMock(return_value="sent")):
        out = apprise_deliver.run(str(uuid4()), str(uuid4()), "T", "B")
    assert out == {"status": "sent"}
