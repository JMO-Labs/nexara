"""
@file test_home_needs_api.py
@brief Tests for GET /api/v1/home/needs.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.home_needs import HomeNeedsResponse


@pytest.mark.asyncio
async def test_needs_unauthenticated(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/api/v1/home/needs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_needs_returns_shape(test_app):
    from app.api.v1 import home_needs as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    svc = AsyncMock()
    svc.get.return_value = HomeNeedsResponse(rsvps=[], polls=[], prompt=None, list_items=None)

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            resp = await c.get("/api/v1/home/needs")
        assert resp.status_code == 200
        assert resp.json() == {"rsvps": [], "polls": [], "prompt": None, "list_items": None}
    finally:
        test_app.dependency_overrides.clear()
