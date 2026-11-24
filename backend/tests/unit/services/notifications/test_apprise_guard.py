"""@file test_apprise_guard.py
@brief SSRF guard, send-time recheck and admin_alert dedupe.
"""

import socket
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services.notifications.apprise_guard import check_apprise_url


def test_member_loopback_blocked() -> None:
    with pytest.raises(AppError) as ei:
        check_apprise_url("json://127.0.0.1/x", allow_local=False)
    assert ei.value.code == "apprise_url_blocked" and ei.value.status_code == 422


def test_member_private_blocked() -> None:
    with pytest.raises(AppError):
        check_apprise_url("json://10.0.0.5", allow_local=False)


def test_member_allow_local_ok() -> None:
    check_apprise_url("json://10.0.0.5", allow_local=True)


def test_admin_local_ntfy_ok() -> None:
    check_apprise_url("ntfy://192.168.1.10/topic", allow_local=True)


def test_hostless_scheme_ok() -> None:
    with patch("socket.getaddrinfo", side_effect=AssertionError("no DNS")):
        check_apprise_url(
            "tgram://123456789:abcdefghijklmnopqrstuvwxyzabcdefghi/12345", allow_local=False
        )


def test_public_host_ok() -> None:
    info = [(socket.AF_INET, 0, 0, "", ("93.184.216.34", 0))]
    with patch("socket.getaddrinfo", return_value=info):
        check_apprise_url("json://example.com/x", allow_local=False)


def test_dns_now_private_blocked() -> None:
    info = [(socket.AF_INET, 0, 0, "", ("10.1.2.3", 0))]
    with patch("socket.getaddrinfo", return_value=info), pytest.raises(AppError):
        check_apprise_url("json://rebind.example.com/x", allow_local=False)


def test_dns_failure_blocked_for_members_skipped_for_admin() -> None:
    with patch("socket.getaddrinfo", side_effect=socket.gaierror):
        with pytest.raises(AppError):
            check_apprise_url("json://nope.example.com/x", allow_local=False)
        check_apprise_url("json://nope.example.com/x", allow_local=True)


async def test_send_time_recheck_blocks() -> None:
    from app.tasks.notification_tasks import _apprise_deliver_async

    row = MagicMock(apprise_url="json://rebind.example.com/x", enabled=True, is_admin_target=False)
    repo = AsyncMock()
    repo.get.return_value = row
    repo.allow_local.return_value = False
    info = [(socket.AF_INET, 0, 0, "", ("10.1.2.3", 0))]
    with patch("socket.getaddrinfo", return_value=info):
        out = await _apprise_deliver_async(repo, uuid.uuid4(), "t", "b")
    assert out == "blocked"
    repo.record_failure.assert_awaited_once()


async def test_admin_alert_dedupes() -> None:
    from app.services import admin_alerts

    redis = MagicMock()
    redis.set = AsyncMock(side_effect=[True, None])
    send = AsyncMock()
    with (
        patch.object(admin_alerts, "get_pool", return_value=redis),
        patch.object(admin_alerts, "_deliver", send),
    ):
        s, cid = MagicMock(), uuid.uuid4()
        await admin_alerts.admin_alert(s, cid, "signin_burst", {"ip": "1.2.3.4"})
        await admin_alerts.admin_alert(s, cid, "signin_burst", {"ip": "1.2.3.4"})
    assert send.await_count == 1
    assert redis.set.await_args.kwargs == {"nx": True, "ex": 1800}


async def test_admin_alert_sends_when_valkey_down() -> None:
    from app.services import admin_alerts

    redis = MagicMock()
    redis.set = AsyncMock(side_effect=OSError("down"))
    send = AsyncMock()
    with (
        patch.object(admin_alerts, "get_pool", return_value=redis),
        patch.object(admin_alerts, "_deliver", send),
    ):
        await admin_alerts.admin_alert(MagicMock(), uuid.uuid4(), "disk_high", {})
    send.assert_awaited_once()
