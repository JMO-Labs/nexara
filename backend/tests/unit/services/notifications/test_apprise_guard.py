"""@file test_apprise_guard.py
@brief SSRF guard, send-time recheck and admin_alert dedupe.
"""

import socket
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services.notifications.apprise_guard import build_apprise, check_apprise_url


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


@pytest.mark.parametrize(
    "addr,blocked",
    [
        ("100.64.0.1", True),
        ("::ffff:127.0.0.1", True),
        ("2002:7f00:1::1", True),
        ("64:ff9b::a00:5", True),
        ("8.8.8.8", False),
    ],
)
def test_ip_classification(addr: str, blocked: bool) -> None:
    from app.services.notifications.apprise_guard import _blocked

    assert _blocked(addr) is blocked


def test_mailto_smtp_param_blocked() -> None:
    info = [(socket.AF_INET, 0, 0, "", ("93.184.216.34", 0))]
    with patch(
        "socket.getaddrinfo",
        side_effect=lambda h, *a: info if h == "example.com" else [(2, 0, 0, "", ("127.0.0.1", 0))],
    ):
        with pytest.raises(AppError):
            check_apprise_url("mailto://u:p@example.com?smtp=127.0.0.1", allow_local=False)


def test_unparsable_url_blocked() -> None:
    with pytest.raises(AppError):
        check_apprise_url("notascheme://x", allow_local=False)


def test_member_sender_has_redirects_off_even_with_url_param() -> None:
    a = build_apprise("json://example.com/x?redirect=yes", allow_local=False)
    assert all(p.redirects is False for p in a)
    assert all(p.redirects for p in build_apprise("json://example.com/x", allow_local=True))


def test_ntfy_short_form_cloud_mode_skips_dns() -> None:
    with patch("socket.getaddrinfo", side_effect=AssertionError("no DNS")):
        check_apprise_url("ntfy://mytopic", allow_local=False)


async def test_admin_alert_logs_when_notify_returns_false() -> None:
    from app.services import admin_alerts

    target = MagicMock()
    target.id = uuid.uuid4()
    target.apprise_url = "ntfy://ntfy.sh/t"
    repo = MagicMock()
    repo.list_admin_targets = AsyncMock(return_value=[target])
    apobj = MagicMock()
    apobj.notify.return_value = False
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    with (
        patch.object(admin_alerts, "AppriseRepository", return_value=repo),
        patch.object(admin_alerts, "build_apprise", return_value=apobj),
        patch.object(admin_alerts, "build_notification_service", return_value=MagicMock()),
        patch.object(admin_alerts, "logger") as log,
    ):
        await admin_alerts.deliver_apprise(session, uuid.uuid4(), "msg")
    log.warning.assert_any_call("admin_alert.apprise_failed", target_id=str(target.id))


async def test_admin_alert_enqueues_apprise_off_request_path() -> None:
    from app.services import admin_alerts

    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    cid = uuid.uuid4()
    with (
        patch("app.tasks.admin_alert_tasks.send_apprise_alert.delay") as delay,
        patch.object(admin_alerts, "build_notification_service", return_value=MagicMock()),
        patch.object(admin_alerts, "deliver_apprise", AsyncMock()) as inline,
    ):
        await admin_alerts._deliver(session, cid, "disk_high", "msg")
    delay.assert_called_once_with(str(cid), "msg")
    inline.assert_not_awaited()
