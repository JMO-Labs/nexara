"""
@file test_signin_log.py
@brief Unit tests for sign-in log: UA parsing, recording, new-device alerts, burst alert.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.auth import signin_log
from app.services.auth.signin_log import parse_device, record_signin, record_signin_safe

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
UID = uuid.uuid4()
IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _req(ip: str | None = "203.0.113.5", ua: str | None = CHROME_WIN):
    return SimpleNamespace(
        client=SimpleNamespace(host=ip) if ip else None,
        headers={"user-agent": ua} if ua else {},
    )


@pytest.mark.parametrize(
    ("ua", "expected"),
    [
        (IPHONE, "Safari on iOS"),
        (CHROME_WIN, "Chrome on Windows"),
        (
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Firefox on Linux",
        ),
        (CHROME_WIN + " Edg/120.0", "Edge on Windows"),
        ("Mozilla/5.0 (Linux; Android 14) Chrome/120.0 Mobile Safari/537", "Chrome on Android"),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17 Safari/605.1.15",
            "Safari on macOS",
        ),
        ("curl/8.0", "Unknown device"),
        (None, "Unknown device"),
        ("", "Unknown device"),
    ],
)
def test_parse_device(ua, expected):
    assert parse_device(ua) == expected


@pytest.fixture
def repo():
    r = MagicMock()
    r.add = AsyncMock(side_effect=lambda e: e)
    r.has_success_with_device = AsyncMock(return_value=True)
    r.has_any_success = AsyncMock(return_value=True)
    r.count_failures = AsyncMock(return_value=1)
    return r


@pytest.fixture
def notifier():
    n = MagicMock()
    n.notify = AsyncMock()
    return n


async def _rec(repo, notifier, **kw):
    args = {
        "community_id": CID,
        "user_id": UID,
        "email": "A@X.com",
        "method": "password",
        "success": True,
        "reason": None,
        "request": _req(),
    }
    args.update(kw)
    with patch.object(signin_log, "SigninRepository", return_value=repo):
        return await record_signin(AsyncMock(), notifier=notifier, **args)


async def test_wrong_password_records_failure(repo, notifier):
    ev = await _rec(repo, notifier, success=False, reason="bad_password")
    assert ev.success is False
    assert ev.reason == "bad_password"
    assert ev.email_tried == "a@x.com"
    assert ev.method == "password"
    assert ev.device == "Chrome on Windows"
    notifier.notify.assert_not_awaited()


async def test_email_truncated_and_lowercased(repo, notifier):
    ev = await _rec(repo, notifier, email="A" * 300, success=False, reason="x")
    assert ev.email_tried == "a" * 254


async def test_sso_success_records_method(repo, notifier):
    ev = await _rec(repo, notifier, method="sso", email=None)
    assert ev.method == "sso"
    assert ev.success is True


async def test_same_device_no_notification(repo, notifier):
    await _rec(repo, notifier)
    notifier.notify.assert_not_awaited()


async def test_new_device_notifies(repo, notifier):
    repo.has_success_with_device.return_value = False
    await _rec(repo, notifier, request=_req(ua=IPHONE))
    notifier.notify.assert_awaited_once()
    args = notifier.notify.await_args
    assert args.args[0] == UID
    assert args.args[1] == "new_signin"
    assert args.args[2]["device"] == "Safari on iOS"
    assert args.args[2]["ip"] == "203.0.113.5"


async def test_first_ever_login_does_not_notify(repo, notifier):
    repo.has_success_with_device.return_value = False
    repo.has_any_success.return_value = False
    await _rec(repo, notifier)
    notifier.notify.assert_not_awaited()


async def test_missing_request_is_unknown_device(repo, notifier):
    ev = await _rec(repo, notifier, request=None)
    assert ev.device == "Unknown device"
    assert ev.ip is None


async def test_invalid_ip_stored_as_none(repo, notifier):
    ev = await _rec(repo, notifier, request=_req(ip="testclient"))
    assert ev.ip is None


async def test_burst_logged_once_per_window(repo, notifier):
    repo.count_failures.return_value = 10
    redis = MagicMock()
    redis.set = AsyncMock(side_effect=[True, None])
    with (
        patch.object(signin_log, "get_pool", return_value=redis),
        patch.object(signin_log, "logger") as log,
    ):
        for _ in range(2):
            await _rec(repo, notifier, success=False, reason="bad_password")
    redis.set.assert_awaited_with("signin:burst:203.0.113.5", "1", nx=True, ex=600)
    events = [c.args[0] for c in log.warning.call_args_list]
    assert events.count("security.signin_burst") == 1


async def test_below_threshold_no_burst(repo, notifier):
    repo.count_failures.return_value = 9
    with patch.object(signin_log, "get_pool") as pool:
        await _rec(repo, notifier, success=False, reason="bad_password")
    pool.assert_not_called()


async def test_safe_wrapper_swallows_errors():
    session = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock()
    session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=False)
    with (
        patch.object(signin_log, "record_signin", AsyncMock(side_effect=RuntimeError("db"))),
        patch.object(signin_log, "logger") as log,
    ):
        out = await record_signin_safe(
            session,
            community_id=CID,
            user_id=None,
            email="a@b.c",
            method="password",
            success=False,
            reason="x",
            request=None,
        )
    assert out is None
    assert log.warning.call_args.args[0] == "signin.record_failed"
