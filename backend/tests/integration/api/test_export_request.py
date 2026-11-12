"""
@file test_export_request.py
@brief Route-level tests for the data export request API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import export
from app.core.dependencies import get_current_user
from app.models.user_export import UserExport
from app.repositories.user_export_repo import UserExportRepository


class FakeRedis:
    """@brief Minimal in-memory stand-in for the Redis ``set`` NX/EX call."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        self.ttls[key] = ex
        return True


def _export(user_id, status="pending", **kw) -> MagicMock:
    e = MagicMock(spec=UserExport)
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.status = status
    e.created_at = datetime.now(UTC)
    e.ready_at = kw.get("ready_at")
    e.expires_at = kw.get("expires_at")
    e.file_size_bytes = kw.get("file_size_bytes")
    return e


@pytest.fixture
def ctx(test_app):
    """@brief Authenticated client with repo, redis, and enqueue overridden."""
    user = MagicMock()
    user.id = uuid.uuid4()
    repo = AsyncMock(spec=UserExportRepository)
    redis = FakeRedis()
    enqueue = MagicMock()
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[export._get_repo] = lambda: repo
    test_app.dependency_overrides[export._get_redis] = lambda: redis
    test_app.dependency_overrides[export._get_enqueue] = lambda: enqueue
    client = AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    yield client, user, repo, redis, enqueue
    test_app.dependency_overrides.clear()


async def test_request_creates_export(ctx):
    client, user, repo, redis, enqueue = ctx
    repo.create_export.return_value = _export(user.id)
    async with client as c:
        resp = await c.post("/api/v1/export/request")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["export_id"] == str(repo.create_export.return_value.id)
    enqueue.assert_called_once_with(str(repo.create_export.return_value.id))
    (key,) = redis.store
    assert key.startswith(f"export_request:{user.id}:")
    assert redis.ttls[key] == 86400


async def test_rate_limit_enforced(ctx):
    client, user, repo, _, enqueue = ctx
    repo.create_export.return_value = _export(user.id)
    async with client as c:
        first = await c.post("/api/v1/export/request")
        second = await c.post("/api/v1/export/request")
    assert first.status_code < 300
    assert second.status_code == 429
    err = second.json()["error"]
    assert err["message"] == "You can request one export per day"
    assert repo.create_export.await_count == 1
    assert enqueue.call_count == 1


async def test_status_ready_has_download_url(ctx):
    client, user, repo, _, _ = ctx
    now = datetime.now(UTC)
    e = _export(
        user.id,
        "ready",
        ready_at=now,
        expires_at=now + timedelta(hours=48),
        file_size_bytes=10,
    )
    repo.get_by_id.return_value = e
    async with client as c:
        resp = await c.get(f"/api/v1/export/{e.id}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["download_url"]
    assert body["file_size_bytes"] == 10


async def test_status_expired_has_no_download_url(ctx):
    client, user, repo, _, _ = ctx
    past = datetime.now(UTC) - timedelta(hours=1)
    e = _export(user.id, "ready", ready_at=past - timedelta(hours=48), expires_at=past)
    repo.get_by_id.return_value = e
    async with client as c:
        resp = await c.get(f"/api/v1/export/{e.id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "expired"
    assert resp.json()["download_url"] is None


async def test_status_other_users_export_forbidden(ctx):
    client, _, repo, _, _ = ctx
    e = _export(uuid.uuid4())
    repo.get_by_id.return_value = e
    async with client as c:
        resp = await c.get(f"/api/v1/export/{e.id}/status")
    assert resp.status_code in (403, 404)
    assert "error" in resp.json()


async def test_status_missing_is_404(ctx):
    client, _, repo, _, _ = ctx
    repo.get_by_id.return_value = None
    async with client as c:
        resp = await c.get(f"/api/v1/export/{uuid.uuid4()}/status")
    assert resp.status_code == 404
