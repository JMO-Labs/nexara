"""
@file test_home_feed_api.py
@brief Tests for GET /api/v1/home/feed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.home_feed import HomeFeedResponse


@pytest.mark.asyncio
async def test_feed_unauthenticated(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/api/v1/home/feed")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_feed_returns_discriminated_items(test_app):
    from app.api.v1 import home_feed as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    pid = uuid.uuid4()
    svc = AsyncMock()
    svc.list.return_value = HomeFeedResponse(
        items=[
            {
                "kind": "post",
                "id": pid,
                "created_at": datetime(2026, 10, 20, tzinfo=UTC),
                "post": {"id": str(pid), "content": "hi"},
            }
        ],
        next_cursor=None,
    )

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            resp = await c.get("/api/v1/home/feed?limit=5")
            bad = await c.get("/api/v1/home/feed?limit=99")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["kind"] == "post"
        assert body["items"][0]["post"]["content"] == "hi"
        assert body["next_cursor"] is None
        assert svc.list.call_args.args[2] == 5
        assert bad.status_code == 422
    finally:
        test_app.dependency_overrides.clear()
