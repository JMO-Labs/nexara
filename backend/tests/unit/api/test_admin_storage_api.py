"""
@file test_admin_storage_api.py
@brief Unit tests for admin storage analytics endpoints.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.schemas.admin_storage import StorageCurrent, StorageResponse, UserStoragePage

BASE = "/api/v1/admin/storage"


@pytest.fixture
def role():
    """@brief Mutable holder for the authenticated user's role."""
    return {"value": "admin"}


@pytest.fixture
def auth(test_app, role):
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()

    async def _override():
        user.role = role["value"]
        return user

    test_app.dependency_overrides[get_current_user] = _override
    yield user
    test_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def service():
    with patch("app.api.v1.admin_storage.AdminStorageService") as cls:
        svc = AsyncMock()
        cls.return_value = svc
        yield svc


async def _get(test_app, url: str):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.get(url)


@pytest.mark.asyncio
async def test_get_storage_delegates_with_days(test_app, auth, service):
    service.get_overview = AsyncMock(
        return_value=StorageResponse(
            current=StorageCurrent(total_bytes=5, by_category={"images": 5}),
            snapshots=[],
            per_user=[],
        )
    )
    resp = await _get(test_app, f"{BASE}?days=7")
    assert resp.status_code == 200
    assert resp.json()["current"]["total_bytes"] == 5
    service.get_overview.assert_awaited_once_with(days=7)


@pytest.mark.asyncio
async def test_list_users_delegates_with_paging(test_app, auth, service):
    service.list_users = AsyncMock(
        return_value=UserStoragePage(items=[], total=0, page=2, page_size=10)
    )
    resp = await _get(test_app, f"{BASE}/users?page=2&page_size=10")
    assert resp.status_code == 200
    assert resp.json()["page"] == 2
    service.list_users.assert_awaited_once_with(page=2, page_size=10)


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["", "/users"])
async def test_non_admin_forbidden(test_app, auth, role, service, path):
    role["value"] = "member"
    assert (await _get(test_app, BASE + path)).status_code == 403


@pytest.mark.asyncio
async def test_build_service_uses_community_setting():
    from app.api.v1.admin_storage import _build_service

    settings = MagicMock(COMMUNITY_ID="00000000-0000-0000-0000-000000000001")
    svc = _build_service(db=MagicMock(), settings=settings)
    assert svc._community_id == uuid.UUID(settings.COMMUNITY_ID)
