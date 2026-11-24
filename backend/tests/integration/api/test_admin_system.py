"""
@file test_admin_system.py
@brief Integration tests for GET /api/v1/admin/system.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.services import system_health as sh

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _client(test_app, role):
    user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
    test_app.dependency_overrides[get_current_user] = lambda: user
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


async def test_non_admin_forbidden(test_app) -> None:
    async with _client(test_app, "member") as c:
        r = await c.get("/api/v1/admin/system")
    test_app.dependency_overrides.clear()
    assert r.status_code == 403


async def test_valkey_down_still_200(test_app) -> None:
    sh._cache = None
    redis = MagicMock()
    redis.ping = AsyncMock(side_effect=OSError("down"))
    redis.get = AsyncMock(side_effect=OSError("down"))
    redis.llen = AsyncMock(side_effect=OSError("down"))
    with (
        patch.object(sh, "get_pool", return_value=redis),
        patch.object(sh, "_ping_workers", return_value={"w": {"ok": "pong"}}),
    ):
        async with _client(test_app, "admin") as c:
            r = await c.get("/api/v1/admin/system")
            r2 = await c.get("/api/v1/admin/system")
    test_app.dependency_overrides.clear()
    sh._cache = None
    assert r.status_code == 200
    body = r.json()
    comps = {x["name"]: x for x in body["components"]}
    assert comps["valkey"]["status"] == "down"
    assert comps["database"]["status"] in ("ok", "warn")
    assert comps["workers"]["status"] == "ok"
    assert body["runtime"]["version"]
    assert "redis://" not in r.text
    assert r2.json() == body  # cached
