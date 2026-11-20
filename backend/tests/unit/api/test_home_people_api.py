"""
@file test_home_people_api.py
@brief Tests for GET /api/v1/home/people.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.home_people import HomePeopleResponse


@pytest.mark.asyncio
async def test_people_unauthenticated(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/api/v1/home/people")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_people_returns_items_and_validates_limit(test_app):
    from app.api.v1 import home_people as mod
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    pid = uuid.uuid4()
    svc = AsyncMock()
    svc.list.return_value = HomePeopleResponse(
        items=[
            {
                "user_id": pid,
                "username": "ruth",
                "display_name": "Ruth",
                "online": True,
                "shared_groups": [],
            }
        ]
    )

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            resp = await c.get("/api/v1/home/people?limit=5")
            bad = await c.get("/api/v1/home/people?limit=99")
            zero = await c.get("/api/v1/home/people?limit=0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["display_name"] == "Ruth"
        assert body["items"][0]["online"] is True
        assert body["items"][0]["birthday_in_days"] is None
        assert svc.list.call_args.args[1] == 5
        assert bad.status_code == 422 and zero.status_code == 422
    finally:
        test_app.dependency_overrides.clear()
