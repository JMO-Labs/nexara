"""
@file test_admin_simple_mode_api.py
@brief PATCH /api/v1/admin/users/{id}/settings is admin only.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import admin as admin_module
from app.core.dependencies import get_current_user
from app.models.user import User


def _user(role: str) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = role
    u.is_active = True
    return u


async def _patch(test_app, role: str, svc: AsyncMock):
    u = _user(role)
    test_app.dependency_overrides[get_current_user] = lambda: u
    test_app.dependency_overrides[admin_module._build_service] = lambda: svc
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            return await c.patch(
                f"/api/v1/admin/users/{uuid.uuid4()}/settings", json={"simple_mode": True}
            )
    finally:
        test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_member_forbidden(test_app):
    svc = AsyncMock()
    r = await _patch(test_app, "member", svc)
    assert r.status_code == 403
    svc.set_simple_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_ok(test_app):
    svc = AsyncMock()
    r = await _patch(test_app, "admin", svc)
    assert r.status_code == 200
    svc.set_simple_mode.assert_awaited_once()
