"""
@file test_push_payload.py
@brief Tests for push payload building, 404 cleanup and per-device management.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.models.notification import Notification, PushSubscription
from app.repositories.push_repo import PushSubscriptionRepository
from app.services.notifications.channels.push import build_push_payload
from app.services.push_service import PushService, endpoint_hash

USER_ID = uuid.uuid4()
COMMUNITY_ID = uuid.uuid4()


def _notif(type_: str, payload: dict) -> MagicMock:
    n = MagicMock(spec=Notification)
    n.type = type_
    n.payload = payload
    return n


def test_comment_payload_title_is_actor_and_tag_is_post() -> None:
    pid = str(uuid.uuid4())
    n = _notif(
        "comment",
        {
            "actor_name": "Maya Chen",
            "message": "Maya Chen commented on your post",
            "link": f"/app/post/{pid}",
            "post_id": pid,
        },
    )
    assert build_push_payload(n) == {
        "title": "Maya Chen",
        "body": "commented on your post",
        "url": f"/app/post/{pid}",
        "tag": f"comment:{pid}",
    }


def test_payload_without_actor_falls_back_to_label_and_type_tag() -> None:
    p = build_push_payload(_notif("system", {"message": "Backup done"}))
    assert p["title"] == "System"
    assert p["body"] == "Backup done"
    assert p["tag"] == "system"
    assert p["url"] is None


def test_tag_uses_channel_and_event_ids() -> None:
    assert build_push_payload(_notif("x", {"message": "m", "channel_id": "c1"}))["tag"] == "x:c1"
    assert build_push_payload(_notif("x", {"message": "m", "event_id": "e1"}))["tag"] == "x:e1"


def _svc(repo: AsyncMock) -> PushService:
    return PushService(repo, AsyncMock(), COMMUNITY_ID, settings=MagicMock())


def _sub(user_id: uuid.UUID = USER_ID) -> MagicMock:
    s = MagicMock(spec=PushSubscription)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.endpoint = "https://push.example.com/abc"
    s.p256dh = "k"
    s.auth = "a"
    s.name = None
    s.user_agent = "Mozilla/5.0 (Linux; Android 14) Chrome/120.0 Mobile Safari/537.36"
    s.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    s.last_used_at = None
    return s


async def test_404_deletes_subscription() -> None:
    from pywebpush import WebPushException

    repo = AsyncMock(spec=PushSubscriptionRepository)
    sub = _sub()
    repo.list_for_user.return_value = [sub]
    svc = PushService(
        repo,
        AsyncMock(),
        COMMUNITY_ID,
        settings=MagicMock(VAPID_PRIVATE_KEY="p", VAPID_PUBLIC_KEY="q", SMTP_FROM="a@b.c"),
    )
    resp = MagicMock(status_code=404)
    with patch("pywebpush.webpush", side_effect=WebPushException("nf", response=resp)):
        await svc.send_push(USER_ID, "t", "b", "/", tag="x", badge_count=3)
    repo.cleanup_stale.assert_awaited_once_with(sub.endpoint)


async def test_success_sets_last_used_and_payload_fields() -> None:
    repo = AsyncMock(spec=PushSubscriptionRepository)
    sub = _sub()
    repo.list_for_user.return_value = [sub]
    svc = PushService(
        repo,
        AsyncMock(),
        COMMUNITY_ID,
        settings=MagicMock(VAPID_PRIVATE_KEY="p", VAPID_PUBLIC_KEY="q", SMTP_FROM="a@b.c"),
    )
    with patch("pywebpush.webpush") as wp:
        await svc.send_push(USER_ID, "t", "b", "/u", tag="comment:1", badge_count=4)
    import json

    data = json.loads(wp.call_args.kwargs["data"])
    assert data == {"title": "t", "body": "b", "url": "/u", "tag": "comment:1", "badge_count": 4}
    repo.touch_last_used.assert_awaited_once_with(sub.id)


async def test_list_devices_hides_endpoint_and_names_from_ua() -> None:
    repo = AsyncMock(spec=PushSubscriptionRepository)
    sub = _sub()
    repo.list_devices.return_value = [sub]
    out = await _svc(repo).list_devices(USER_ID)
    repo.list_devices.assert_awaited_once_with(USER_ID, COMMUNITY_ID)
    dumped = out[0].model_dump()
    assert dumped["name"] == "Chrome on Android"
    assert dumped["endpoint_hash"] == endpoint_hash(sub.endpoint)
    assert len(dumped["endpoint_hash"]) == 16
    assert "endpoint" not in dumped and "p256dh" not in dumped and "auth" not in dumped


async def test_rename_and_delete_device_scoped_and_404() -> None:
    repo = AsyncMock(spec=PushSubscriptionRepository)
    sub = _sub()
    repo.get_device.return_value = sub
    out = await _svc(repo).rename_device(USER_ID, sub.id, "Mum's phone")
    repo.get_device.assert_awaited_with(sub.id, USER_ID, COMMUNITY_ID)
    assert sub.name == "Mum's phone"
    assert out.name == "Mum's phone"

    repo.delete_device.return_value = False
    with pytest.raises(NotFoundError):
        await _svc(repo).delete_device(USER_ID, sub.id)
    repo.get_device.return_value = None
    with pytest.raises(NotFoundError):
        await _svc(repo).rename_device(USER_ID, sub.id, "x")


async def test_subscribe_sets_default_name_from_ua() -> None:
    repo = AsyncMock(spec=PushSubscriptionRepository)
    repo.find_by_endpoint.return_value = None
    repo.create.side_effect = lambda s: s
    sub = await _svc(repo).subscribe(
        USER_ID, "https://p/e", "k", "a", "Mozilla/5.0 (iPhone) Safari/604.1"
    )
    assert sub.name == "Safari on iOS"
