"""
@file test_countdowns.py
@brief Route tests for /api/v1/countdowns (mocked service).
"""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.deps_countdown import get_countdown_service
from app.core.exceptions import NotFoundError
from app.schemas.countdown import CountdownResponse
from app.services.countdown_service import CountdownService


def _resp() -> CountdownResponse:
    return CountdownResponse(
        id=uuid.uuid4(), author_id=uuid.uuid4(), title="t", target_date=date(2030, 1, 1),
        tz="UTC", repeat_yearly=False, visibility="community", days_left=5,
        next_date=date(2030, 1, 1), following=True, follower_count=1,
    )  # fmt: skip


@pytest.fixture
def env(test_app):
    svc = AsyncMock(spec=CountdownService)
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    test_app.dependency_overrides[get_countdown_service] = lambda: svc
    yield svc, AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


async def test_create_and_following_route_not_shadowed(env):
    svc, c = env
    svc.create.return_value = _resp()
    svc.list_following.return_value = [_resp()]
    async with c:
        r = await c.post("/api/v1/countdowns", json={"title": "t", "target_date": "2030-01-01"})
        assert r.status_code == 201 and r.json()["days_left"] == 5
        r = await c.get("/api/v1/countdowns/following?include_done=true")
        assert r.status_code == 200 and len(r.json()) == 1
        svc.list_following.assert_awaited_with(svc.list_following.await_args.args[0], True)


async def test_get_404_and_delete_204(env):
    svc, c = env
    svc.get.side_effect = NotFoundError("nope")
    svc.follow.return_value = _resp()
    async with c:
        assert (await c.get(f"/api/v1/countdowns/{uuid.uuid4()}")).status_code == 404
        assert (await c.delete(f"/api/v1/countdowns/{uuid.uuid4()}")).status_code == 204
        assert (await c.post(f"/api/v1/countdowns/{uuid.uuid4()}/follow")).status_code == 200
