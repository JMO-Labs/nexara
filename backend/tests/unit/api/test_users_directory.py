"""
@file test_users_directory.py
@brief Tests for GET /api/v1/users/directory.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.people_directory import DirectoryResponse


@pytest.mark.asyncio
async def test_directory_unauthenticated(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/api/v1/users/directory")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_directory_returns_items_and_passes_params(test_app):
    from app.api.v1 import users_directory as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = "member"
    svc = AsyncMock()
    svc.list.return_value = DirectoryResponse(
        items=[
            {
                "user_id": uuid.uuid4(),
                "username": "ruth",
                "display_name": "Ruth",
                "online": True,
                "shared_groups": [],
            }
        ],
        next_cursor="24",
    )

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            ok = await c.get("/api/v1/users/directory?q=ru&filter=online&limit=5&cursor=24")
            bad_filter = await c.get("/api/v1/users/directory?filter=nope")
            bad_limit = await c.get("/api/v1/users/directory?limit=500")
        assert ok.status_code == 200
        body = ok.json()
        assert body["items"][0]["display_name"] == "Ruth"
        assert body["next_cursor"] == "24"
        kw = svc.list.call_args.kwargs
        assert kw == {"q": "ru", "filter": "online", "limit": 5, "cursor": "24"}
        assert bad_filter.status_code == 422 and bad_limit.status_code == 422
    finally:
        test_app.dependency_overrides.clear()


async def test_directory_rejects_roles_outside_admin_member(test_app):
    """@brief Same gate as GET /users: only admins and members may browse people."""
    from app.api.v1 import users_directory as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = "guest"

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: AsyncMock()
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            r = await c.get("/api/v1/users/directory")
        assert r.status_code == 403
    finally:
        test_app.dependency_overrides.clear()
