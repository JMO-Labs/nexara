"""
@file test_snooze_api.py
@brief Route tests for /notifications/snooze and PATCH /preferences DnD fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import notifications as mod
from app.core.dependencies import get_current_user
from app.core.exceptions import AppError
from app.schemas.notification import NotificationPreferences
from app.services.notification_service import NotificationService

BASE = "/api/v1/notifications"


def _prefs(tz: str = "UTC", **kw) -> NotificationPreferences:
    data = {
        "notification_prefs": {},
        "dnd_schedule": None,
        "dnd_until": None,
        "dnd_timezone": tz,
        "digest_cadence": {},
    }
    data.update(kw)
    return NotificationPreferences(**data)


@pytest.fixture
def service() -> AsyncMock:
    svc = AsyncMock(spec=NotificationService)
    svc.get_preferences.return_value = _prefs()
    return svc


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    return u


@pytest.fixture
def client(test_app, service, user):
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[mod._build_service] = lambda: service
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t")
    test_app.dependency_overrides.clear()


async def test_snooze_1h(client, service, user):
    async with client as c:
        r = await c.post(f"{BASE}/snooze", json={"duration": "1h"})
    assert r.status_code == 200
    uid, until = service.snooze.await_args.args
    assert uid == user.id
    delta = until - datetime.now(UTC)
    assert timedelta(minutes=59) < delta <= timedelta(hours=1)


async def test_snooze_until_morning_uses_user_tz(client, service):
    service.get_preferences.return_value = _prefs("Asia/Tokyo")
    async with client as c:
        r = await c.post(f"{BASE}/snooze", json={"duration": "until_morning"})
    assert r.status_code == 200
    until = service.snooze.await_args.args[1]
    assert until.astimezone(UTC) > datetime.now(UTC)
    assert until.astimezone(UTC).hour == 22  # 07:00 JST == 22:00 UTC


async def test_snooze_iso8601(client, service):
    end = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
    async with client as c:
        r = await c.post(f"{BASE}/snooze", json={"duration": end.isoformat()})
    assert r.status_code == 200
    assert service.snooze.await_args.args[1] == end


@pytest.mark.parametrize("bad", ["soon", "2001-01-01T00:00:00+00:00"])
async def test_snooze_invalid_400(client, service, bad):
    async with client as c:
        r = await c.post(f"{BASE}/snooze", json={"duration": bad})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "NOTIF_PREF_INVALID"
    service.snooze.assert_not_awaited()


async def test_delete_snooze(client, service, user):
    async with client as c:
        r = await c.delete(f"{BASE}/snooze")
    assert r.status_code == 200
    service.clear_snooze.assert_awaited_once_with(user.id)


async def test_patch_preferences_dnd(client, service):
    sched = {"mon": [{"start": "22:00", "end": "07:00"}]}
    service.update_preferences.return_value = _prefs("Europe/Paris", dnd_schedule=sched)
    async with client as c:
        r = await c.patch(
            f"{BASE}/preferences",
            json={"dnd_schedule": sched, "dnd_timezone": "Europe/Paris"},
        )
    assert r.status_code == 200
    assert r.json()["dnd_schedule"] == sched
    assert r.json()["dnd_timezone"] == "Europe/Paris"


async def test_patch_preferences_bad_cadence_400(client, service):
    service.update_preferences.side_effect = AppError(
        code="NOTIF_PREF_INVALID", message="bad", status_code=400
    )
    async with client as c:
        r = await c.patch(f"{BASE}/preferences", json={"digest_cadence": {"mention": "weekly"}})
    assert r.status_code == 400
