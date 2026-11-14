"""
@file test_notifications_prefs_apprise_api.py
@brief Route-level GET/PATCH /preferences apprise flag (real service, mock repos).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import notifications as mod
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService

BASE = "/api/v1/notifications"


def _row() -> MagicMock:
    row = MagicMock()
    row.notification_prefs = {"mention": {"push": True, "apprise": True}}
    row.dnd_schedule = None
    row.dnd_until = None
    row.dnd_timezone = "UTC"
    row.digest_cadence = {}
    return row


@pytest.fixture
def settings_repo() -> AsyncMock:
    repo = AsyncMock(spec=SettingsRepository)
    repo.get_or_create.return_value = _row()
    return repo


@pytest.fixture
async def client(test_app: FastAPI, settings_repo: AsyncMock) -> AsyncIterator[AsyncClient]:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    service = NotificationService(
        AsyncMock(spec=NotificationRepository),
        settings_repo,
        uuid.uuid4(),
        dispatcher=MagicMock(),
    )
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[mod._build_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            yield c
    finally:
        test_app.dependency_overrides.clear()


async def test_get_preferences_shows_apprise_flag(client: AsyncClient) -> None:
    resp = await client.get(f"{BASE}/preferences")
    assert resp.status_code == 200
    assert resp.json()["notification_prefs"]["mention"]["apprise"] is True


async def test_patch_non_bool_apprise_returns_400_envelope(
    client: AsyncClient, settings_repo: AsyncMock
) -> None:
    resp = await client.patch(
        f"{BASE}/preferences", json={"notification_prefs": {"mention": {"apprise": "yes"}}}
    )
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "NOTIF_PREF_INVALID"
    assert err["details"]["field"] == "notification_prefs.mention.apprise"
    settings_repo.update.assert_not_awaited()
