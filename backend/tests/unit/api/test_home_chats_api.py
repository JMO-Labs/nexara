"""
@file test_home_chats_api.py
@brief Tests for GET /api/v1/home/chats and POST /api/v1/chat/channels/{id}/read.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.schemas.home_chats import HomeChatsResponse


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_chats_unauthenticated(test_app):
    async with _client(test_app) as c:
        resp = await c.get("/api/v1/home/chats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chats_shape_and_limit(test_app):
    from app.api.v1 import home_chats as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    cid = uuid.uuid4()
    svc = AsyncMock()
    svc.list.return_value = HomeChatsResponse(
        items=[
            {
                "channel_id": cid,
                "name": "General",
                "channel_type": "community",
                "subgroup_id": None,
                "peer": None,
                "last_message": None,
                "unread_count": 2,
                "mentions_me": False,
                "last_activity_at": "2026-11-19T12:00:00Z",
            }
        ]
    )

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    try:
        async with _client(test_app) as c:
            ok = await c.get("/api/v1/home/chats?limit=3")
            bad = await c.get("/api/v1/home/chats?limit=99")
        assert ok.status_code == 200
        assert ok.json()["items"][0]["unread_count"] == 2
        assert svc.list.call_args.args[1] == 3
        assert bad.status_code == 422
    finally:
        test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_mark_read_204_and_404(test_app):
    from app.api.v1 import chat as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    svc = AsyncMock()

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    cid = uuid.uuid4()
    try:
        async with _client(test_app) as c:
            ok = await c.post(f"/api/v1/chat/channels/{cid}/read")
            svc.mark_read.side_effect = NotFoundError("Channel not found")
            missing = await c.post(f"/api/v1/chat/channels/{cid}/read")
        assert ok.status_code == 204
        assert svc.mark_read.await_count == 2
        assert missing.status_code == 404
        assert "error" in missing.json()
    finally:
        test_app.dependency_overrides.clear()
