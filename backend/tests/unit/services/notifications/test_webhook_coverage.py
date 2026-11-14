"""@file Coverage tests for webhook channel failure, SSRF guard and delivery task."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.models.notification import Notification
from app.repositories.webhook_repo import WebhookRepository
from app.services.notifications import webhook_guard as g
from app.services.notifications.channels.webhook import WebhookChannel
from app.tasks import notification_tasks as nt


async def test_channel_all_enqueues_fail_returns_error() -> None:
    n = MagicMock(spec=Notification)
    n.id, n.user_id, n.community_id, n.type = uuid4(), uuid4(), uuid4(), "new_post"
    sub = MagicMock()
    sub.id = uuid4()
    repo = AsyncMock(spec=WebhookRepository)
    repo.list_matching.return_value = [sub]
    with patch("app.services.notifications.channels.webhook.webhook_deliver") as task:
        task.delay.side_effect = RuntimeError("broker down")
        res = await WebhookChannel(repo).send(n)
    assert res.ok is False
    assert "broker down" in (res.error or "")


async def test_resolve_host_returns_addresses() -> None:
    infos = [(0, 0, 0, "", ("93.184.216.34", 443))]
    loop = MagicMock()
    loop.getaddrinfo = AsyncMock(return_value=infos)
    with patch.object(g.asyncio, "get_running_loop", return_value=loop):
        assert await g.resolve_host("example.com", 443) == ["93.184.216.34"]


async def test_resolve_host_gaierror_becomes_connect_error() -> None:
    loop = MagicMock()
    loop.getaddrinfo = AsyncMock(side_effect=socket.gaierror("nope"))
    with patch.object(g.asyncio, "get_running_loop", return_value=loop):
        with pytest.raises(httpx.ConnectError):
            await g.resolve_host("bad.invalid", 80)


def test_is_global_invalid_and_mapped() -> None:
    assert g._is_global("not-an-ip") is False
    assert g._is_global("::ffff:127.0.0.1") is False
    assert g._is_global("::ffff:8.8.8.8") is True
    assert g._is_global("fe80::1%eth0") is False


@pytest.mark.parametrize("url", ["ftp://example.com/x", "http:///x", "nonsense"])
async def test_blocked_for_bad_scheme_or_host(url: str) -> None:
    assert await g.is_blocked_destination(url, frozenset()) is True


async def test_allowed_host_bypasses_resolution() -> None:
    with patch.object(g, "resolve_host", AsyncMock(side_effect=AssertionError)):
        assert (
            await g.is_blocked_destination("http://Internal.lan/x", frozenset({"internal.lan"}))
            is False
        )


async def test_empty_resolution_is_blocked() -> None:
    with patch.object(g, "resolve_host", AsyncMock(return_value=[])):
        assert await g.is_blocked_destination("https://a.example/x", frozenset()) is True


async def test_default_ports_and_public_ok() -> None:
    rh = AsyncMock(return_value=["8.8.8.8"])
    with patch.object(g, "resolve_host", rh):
        assert await g.is_blocked_destination("https://a.example/x", frozenset()) is False
        assert await g.is_blocked_destination("http://a.example/x", frozenset()) is False
    assert [c.args[1] for c in rh.await_args_list] == [443, 80]


def _patch_session(sub: object, notif: object) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.get = AsyncMock(return_value=notif)
    session.commit = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    repo = MagicMock()
    repo.get = AsyncMock(return_value=sub)
    return cm, repo


@pytest.mark.parametrize("case", ["no_sub", "no_notif", "disabled"])
async def test_deliver_async_skips(case: str) -> None:
    sub = None if case == "no_sub" else MagicMock(enabled=case != "disabled")
    notif = None if case == "no_notif" else MagicMock()
    cm, repo = _patch_session(sub, notif)
    with (
        patch.object(nt, "async_session_factory", return_value=cm),
        patch.object(nt, "WebhookRepository", return_value=repo),
    ):
        out = await nt._webhook_deliver_async(str(uuid4()), str(uuid4()), False)
    assert out == {"status": "skipped"}


@pytest.mark.parametrize("known", [True, False])
async def test_deliver_async_delivers_and_commits(known: bool) -> None:
    cm, repo = _patch_session(MagicMock(enabled=True), MagicMock())
    session = cm.__aenter__.return_value
    reg = MagicMock()
    if known:
        reg.get.return_value = MagicMock(category="social")
    else:
        reg.get.side_effect = KeyError("x")
    deliver = AsyncMock(return_value="delivered")
    with (
        patch.object(nt, "async_session_factory", return_value=cm),
        patch.object(nt, "WebhookRepository", return_value=repo),
        patch.object(nt, "registry", reg),
        patch.object(nt, "deliver_webhook", deliver),
    ):
        out = await nt._webhook_deliver_async(str(uuid4()), str(uuid4()), True)
    assert out == {"status": "delivered"}
    assert deliver.await_args.args[3] == ("social" if known else None)
    assert deliver.await_args.kwargs == {"final_attempt": True}
    session.commit.assert_awaited_once()


async def test_deliver_async_commits_when_delivery_raises() -> None:
    cm, repo = _patch_session(MagicMock(enabled=True), MagicMock())
    session = cm.__aenter__.return_value
    with (
        patch.object(nt, "async_session_factory", return_value=cm),
        patch.object(nt, "WebhookRepository", return_value=repo),
        patch.object(nt, "deliver_webhook", AsyncMock(side_effect=httpx.ConnectError("x"))),
    ):
        with pytest.raises(httpx.ConnectError):
            await nt._webhook_deliver_async(str(uuid4()), str(uuid4()), False)
    session.commit.assert_awaited_once()
