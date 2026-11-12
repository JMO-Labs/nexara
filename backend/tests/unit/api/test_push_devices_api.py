"""
@file test_push_devices_api.py
@brief Route tests for POST/DELETE /api/v1/push/devices.

Uses httpx AsyncClient with mocked PushService and auth dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def client_setup(test_app):
    """@brief Override auth and PushService; yield (app, user, service)."""
    from app.api.v1 import push as push_module
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    service = AsyncMock()

    async def _override_user():
        return user

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[push_module._build_service] = lambda: service
    yield test_app, user, service
    test_app.dependency_overrides.clear()


async def _request(app, method: str, url: str, **kwargs):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


async def test_register_device_returns_201(client_setup):
    app, user, service = client_setup
    device = MagicMock()
    device.id = uuid.uuid4()
    device.platform = "android"
    device.created_at = datetime.now(UTC)
    service.register_device.return_value = device

    resp = await _request(
        app, "POST", "/api/v1/push/devices", json={"platform": "android", "token": "tok"}
    )

    assert resp.status_code == 201
    assert resp.json()["platform"] == "android"
    service.register_device.assert_awaited_once_with(user.id, "android", "tok")


async def test_register_device_rejects_bad_platform(client_setup):
    app, _, _ = client_setup
    resp = await _request(
        app, "POST", "/api/v1/push/devices", json={"platform": "web", "token": "tok"}
    )
    assert resp.status_code == 422


async def test_unregister_device_returns_200(client_setup):
    app, user, service = client_setup
    resp = await _request(app, "DELETE", "/api/v1/push/devices/tok")
    assert resp.status_code == 200
    service.unregister_device.assert_awaited_once_with(user.id, "tok")


async def test_unregister_device_not_owned_returns_404(client_setup):
    app, _, service = client_setup
    service.unregister_device.side_effect = NotFoundError("Device token not found")

    resp = await _request(app, "DELETE", "/api/v1/push/devices/tok")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_register_device_unauthenticated(test_app):
    resp = await _request(
        test_app, "POST", "/api/v1/push/devices", json={"platform": "ios", "token": "t"}
    )
    assert resp.status_code == 401
