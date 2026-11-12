"""
@file test_export_request.py
@brief Route-level tests for the data-export request API.
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

NOW = datetime.now(UTC)


class FakeRedis:
    """@brief Minimal async Valkey stand-in supporting SET NX EX."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys):
        n = 0
        for k in keys:
            n += self.data.pop(k, None) is not None
            self.ttls.pop(k, None)
        return n


def _export(user_id, **kw) -> MagicMock:
    row = MagicMock(spec=UserExport)
    row.id = kw.get("id", uuid.uuid4())
    row.user_id = user_id
    row.status = kw.get("status", "pending")
    row.created_at = NOW
    row.ready_at = kw.get("ready_at")
    row.expires_at = kw.get("expires_at")
    row.file_size_bytes = kw.get("file_size_bytes")
    return row


@pytest.fixture
def user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.community_id = uuid.uuid4()
    return u


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=UserExportRepository)


@pytest.fixture
def redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def enqueue() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(test_app, user, repo, redis, enqueue):
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[export._get_repo] = lambda: repo
    test_app.dependency_overrides[export._get_redis] = lambda: redis
    test_app.dependency_overrides[export._get_enqueue] = lambda: enqueue
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


class TestRequest:
    async def test_creates_export_and_enqueues(self, client, repo, redis, enqueue, user):
        row = _export(user.id)
        repo.create.return_value = row
        async with client as c:
            resp = await c.post("/api/v1/export/request")
        assert resp.status_code == 200
        body = resp.json()
        assert body["export_id"] == str(row.id)
        assert body["status"] == "pending"
        repo.create.assert_awaited_once_with(user.id, user.community_id)
        enqueue.assert_called_once_with(str(row.id))
        key = f"export_request:{user.id}:{datetime.now(UTC).date().isoformat()}"
        assert key in redis.data
        assert redis.ttls[key] == 86400

    async def test_second_request_is_rate_limited(self, client, repo, enqueue, user):
        repo.create.return_value = _export(user.id)
        async with client as c:
            first = await c.post("/api/v1/export/request")
            second = await c.post("/api/v1/export/request")
        assert first.status_code < 300
        assert second.status_code == 429
        err = second.json()["error"]
        assert err["message"] == "You can request one export per day"
        assert repo.create.await_count == 1
        assert enqueue.call_count == 1

    @pytest.mark.parametrize("step", ["create", "commit", "enqueue"])
    async def test_failure_releases_rate_limit_key(self, client, repo, redis, enqueue, user, step):
        target = enqueue if step == "enqueue" else getattr(repo, step)
        target.side_effect = RuntimeError("down")
        repo.create.return_value = _export(user.id)
        async with client as c:
            with pytest.raises(RuntimeError):
                await c.post("/api/v1/export/request")
            assert redis.data == {}
            target.side_effect = None
            retry = await c.post("/api/v1/export/request")
        assert retry.status_code == 200


class TestStatus:
    async def test_ready_has_download_url(self, client, repo, user):
        row = _export(
            user.id,
            status="ready",
            ready_at=NOW,
            expires_at=NOW + timedelta(hours=48),
            file_size_bytes=123,
        )
        repo.get_by_id.return_value = row
        async with client as c:
            resp = await c.get(f"/api/v1/export/{row.id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["file_size_bytes"] == 123
        assert body["download_url"] == f"/api/v1/export/{row.id}/download"
        repo.get_by_id.assert_awaited_once_with(row.id, user.community_id)

    async def test_expired_has_no_download_url(self, client, repo, user):
        row = _export(
            user.id,
            status="ready",
            ready_at=NOW - timedelta(hours=60),
            expires_at=NOW - timedelta(hours=12),
        )
        repo.get_by_id.return_value = row
        async with client as c:
            resp = await c.get(f"/api/v1/export/{row.id}/status")
        body = resp.json()
        assert body["status"] == "expired"
        assert body["download_url"] is None

    async def test_pending_has_no_download_url(self, client, repo, user):
        row = _export(user.id)
        repo.get_by_id.return_value = row
        async with client as c:
            resp = await c.get(f"/api/v1/export/{row.id}/status")
        assert resp.json()["download_url"] is None

    async def test_other_users_export_forbidden(self, client, repo):
        row = _export(uuid.uuid4())
        repo.get_by_id.return_value = row
        async with client as c:
            resp = await c.get(f"/api/v1/export/{row.id}/status")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_missing_is_404(self, client, repo):
        repo.get_by_id.return_value = None
        async with client as c:
            resp = await c.get(f"/api/v1/export/{uuid.uuid4()}/status")
        assert resp.status_code == 404
