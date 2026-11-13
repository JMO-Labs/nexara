"""
@file test_notifications_api.py
@brief Route tests for /api/v1/notifications (service mocked).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import notifications as mod
from app.core.dependencies import get_current_user
from app.core.exceptions import AppError, NotFoundError
from app.models.user import User
from app.schemas.notification import (
    NotificationList,
    NotificationPreferences,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

BASE = "/api/v1/notifications"
NOW = datetime(2026, 1, 2, tzinfo=UTC)


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    return u


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock(spec=NotificationService)


@pytest.fixture
async def client(
    test_app: FastAPI, user: MagicMock, service: AsyncMock
) -> AsyncIterator[AsyncClient]:
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[mod._build_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            yield c
    finally:
        test_app.dependency_overrides.clear()


def _row(user_id: uuid.UUID) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "type": "mention",
        "payload": {"message": "hi"},
        "read_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        "dismissed_at": None,
        "count": 2,
        "actor_ids": [uuid.uuid4()],
    }


# --- /types ---------------------------------------------------------------


async def test_types_returns_registry_with_etag_and_cache(client: AsyncClient) -> None:
    resp = await client.get(f"{BASE}/types")
    assert resp.status_code == 200
    keys = {t["key"] for t in resp.json()}
    assert {"mention", "comment", "system"} <= keys
    assert resp.headers["etag"].startswith('"')
    assert "max-age=3600" in resp.headers["cache-control"]


async def test_types_returns_304_when_etag_matches(client: AsyncClient) -> None:
    etag = (await client.get(f"{BASE}/types")).headers["etag"]
    resp = await client.get(f"{BASE}/types", headers={"If-None-Match": etag})
    assert resp.status_code == 304
    assert resp.headers["etag"] == etag
    assert resp.content == b""


# --- list / active / unread-count ------------------------------------------


async def test_list_passes_filters(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.list_for_user.return_value = NotificationList(items=[_row(user.id)])  # type: ignore[list-item]
    resp = await client.get(
        BASE, params={"limit": 5, "cursor": "c", "type": "mention", "unread_only": "true"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["count"] == 2
    assert len(body["items"][0]["actor_ids"]) == 1
    service.list_for_user.assert_awaited_once_with(
        user.id, cursor="c", limit=5, type="mention", category=None, unread_only=True
    )


async def test_list_rejects_unknown_category(client: AsyncClient) -> None:
    resp = await client.get(BASE, params={"category": "bogus"})
    assert resp.status_code == 422


async def test_list_unknown_type_returns_400(client: AsyncClient, service: AsyncMock) -> None:
    service.list_for_user.side_effect = AppError(
        code="NOTIF_TYPE_UNKNOWN", message="x", status_code=400
    )
    resp = await client.get(BASE, params={"type": "nope"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "NOTIF_TYPE_UNKNOWN"


async def test_active_returns_top_20(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    rows = [MagicMock(**_row(user.id)) for _ in range(2)]
    service.list_active.return_value = rows
    resp = await client.get(f"{BASE}/active")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    service.list_active.assert_awaited_once_with(user.id, limit=20)


async def test_unread_count_by_category(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.get_unread_count.return_value = UnreadCountResponse(
        count=4, by_category={"social": 3, "event": 1}
    )
    resp = await client.get(f"{BASE}/unread-count")
    assert resp.json() == {"count": 4, "by_category": {"social": 3, "event": 1}}
    service.get_unread_count.assert_awaited_once_with(user.id)


# --- read / dismiss ---------------------------------------------------------


async def test_mark_read_ok(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    nid = uuid.uuid4()
    service.mark_read.return_value = True
    resp = await client.post(f"{BASE}/{nid}/read")
    assert resp.status_code == 200
    service.mark_read.assert_awaited_once_with(nid, user.id)


async def test_mark_read_not_owned_returns_404_envelope(
    client: AsyncClient, service: AsyncMock
) -> None:
    service.mark_read.return_value = False
    resp = await client.post(f"{BASE}/{uuid.uuid4()}/read")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_dismiss_ok(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    nid = uuid.uuid4()
    resp = await client.post(f"{BASE}/{nid}/dismiss")
    assert resp.status_code == 200
    service.dismiss.assert_awaited_once_with(user.id, nid)


async def test_dismiss_not_owned_returns_404(client: AsyncClient, service: AsyncMock) -> None:
    service.dismiss.side_effect = NotFoundError("Notification not found")
    resp = await client.post(f"{BASE}/{uuid.uuid4()}/dismiss")
    assert resp.status_code == 404


async def test_read_all_with_filters(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.mark_all_read.return_value = 3
    resp = await client.post(f"{BASE}/read-all", params={"category": "social"})
    assert resp.status_code == 200
    service.mark_all_read.assert_awaited_once_with(user.id, type=None, category="social")


async def test_dismiss_all(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    service.dismiss_all.return_value = 7
    resp = await client.post(f"{BASE}/dismiss-all")
    assert resp.status_code == 200
    service.dismiss_all.assert_awaited_once_with(user.id)


# --- delete -----------------------------------------------------------------


async def test_bulk_delete_with_filters(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.clear_all.return_value = 2
    resp = await client.delete(BASE, params={"type": "mention", "before": NOW.isoformat()})
    assert resp.status_code == 200
    service.clear_all.assert_awaited_once_with(user.id, type="mention", before=NOW)


async def test_delete_one(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    nid = uuid.uuid4()
    resp = await client.delete(f"{BASE}/{nid}")
    assert resp.status_code == 200
    service.delete.assert_awaited_once_with(user.id, nid)


async def test_delete_one_not_owned_returns_404(client: AsyncClient, service: AsyncMock) -> None:
    service.delete.side_effect = NotFoundError("Notification not found")
    resp = await client.delete(f"{BASE}/{uuid.uuid4()}")
    assert resp.status_code == 404


# --- preferences ------------------------------------------------------------


def _prefs() -> NotificationPreferences:
    return NotificationPreferences(
        notification_prefs={"mention": {"email": False}},
        dnd_schedule=None,
        dnd_until=None,
        dnd_timezone="UTC",
        digest_cadence={},
    )


async def test_get_preferences(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    service.get_preferences.return_value = _prefs()
    resp = await client.get(f"{BASE}/preferences")
    assert resp.status_code == 200
    assert resp.json()["notification_prefs"] == {"mention": {"email": False}}
    service.get_preferences.assert_awaited_once_with(user.id)


async def test_patch_preferences_passes_only_set_fields(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.update_preferences.return_value = _prefs()
    resp = await client.patch(f"{BASE}/preferences", json={"dnd_timezone": "Europe/Paris"})
    assert resp.status_code == 200
    args = service.update_preferences.await_args.args
    assert args[0] == user.id
    assert args[1].model_dump(exclude_unset=True) == {"dnd_timezone": "Europe/Paris"}


async def test_patch_preferences_invalid_returns_400(
    client: AsyncClient, service: AsyncMock
) -> None:
    service.update_preferences.side_effect = AppError(
        code="NOTIF_PREF_INVALID", message="bad", status_code=400
    )
    resp = await client.patch(f"{BASE}/preferences", json={"digest_cadence": {"mention": "yearly"}})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "NOTIF_PREF_INVALID"


async def test_routes_require_auth(test_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        resp = await c.get(f"{BASE}/active")
    assert resp.status_code == 401


async def test_snooze_route_sets_until(
    client: AsyncClient, service: AsyncMock, user: MagicMock
) -> None:
    service.get_preferences.return_value = NotificationPreferences(
        notification_prefs={},
        dnd_schedule=None,
        dnd_until=None,
        dnd_timezone="UTC",
        digest_cadence={},
    )
    r = await client.post(f"{BASE}/snooze", json={"duration": "1h"})
    assert r.status_code == 200
    assert service.snooze.await_args.args[0] == user.id


async def test_clear_snooze_route(client: AsyncClient, service: AsyncMock, user: MagicMock) -> None:
    r = await client.delete(f"{BASE}/snooze")
    assert r.status_code == 200
    service.clear_snooze.assert_awaited_once_with(user.id)
