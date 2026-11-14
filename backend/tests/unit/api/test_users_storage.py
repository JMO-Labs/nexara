"""
@file test_users_storage.py
@brief Route tests for GET /api/v1/users/{user_id}/storage.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError
from app.models.user import User
from app.schemas.media import StorageByType, StorageUsageResponse


def _override(test_app, svc: AsyncMock) -> MagicMock:
    from app.api.v1 import users as users_module

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[users_module._build_storage_service] = lambda: svc
    return user


async def test_storage_ok(test_app):
    svc = AsyncMock()
    svc.get_usage.return_value = StorageUsageResponse(
        used_bytes=5, quota_bytes=10, by_type=StorageByType(photos=5)
    )
    user = _override(test_app, svc)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/v1/users/{user.id}/storage")
    finally:
        test_app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json() == {
        "used_bytes": 5,
        "quota_bytes": 10,
        "by_type": {"photos": 5, "videos": 0, "documents": 0, "other": 0},
    }


async def test_storage_forbidden(test_app):
    svc = AsyncMock()
    svc.get_usage.side_effect = AuthorizationError()
    _override(test_app, svc)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/v1/users/{uuid.uuid4()}/storage")
    finally:
        test_app.dependency_overrides.clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTHORIZATION_ERROR"


async def test_storage_unauthenticated(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/users/{uuid.uuid4()}/storage")
    assert resp.status_code == 401


def test_build_storage_service_returns_service():
    from app.api.v1.users import _build_storage_service
    from app.services.storage.usage_service import StorageUsageService

    assert isinstance(_build_storage_service(MagicMock()), StorageUsageService)
