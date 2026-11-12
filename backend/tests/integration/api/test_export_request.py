"""
@file test_export_request.py
@brief Route-level tests for the data export request/status API (nexara#37).

Uses the real ExportService wired to a mocked repository, an in-memory
Valkey fake and a stubbed task enqueuer.
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
from app.services.export_service import ExportService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeValkey:
    """@brief Minimal async INCR/EXPIRE/TTL fake."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttl: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttl[key] = seconds
        return True


def _export(user_id: uuid.UUID, **kw: object) -> MagicMock:
    exp = MagicMock(spec=UserExport)
    exp.id = kw.get("id", uuid.uuid4())
    exp.user_id = user_id
    exp.community_id = COMMUNITY_ID
    exp.status = kw.get("status", "pending")
    exp.created_at = kw.get("created_at", datetime.now(UTC))
    exp.ready_at = kw.get("ready_at")
    exp.expires_at = kw.get("expires_at")
    exp.file_size_bytes = kw.get("file_size_bytes")
    return exp


@pytest.fixture
def user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    return u


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=UserExportRepository)


@pytest.fixture
def valkey() -> FakeValkey:
    return FakeValkey()


@pytest.fixture
def enqueue() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(test_app, user, repo, valkey, enqueue):
    svc = ExportService(repo, COMMUNITY_ID, valkey, enqueue)
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[export._build_service] = lambda: svc
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


class TestRequestExport:
    async def test_request_creates_export(self, client, user, repo, valkey, enqueue):
        created = _export(user.id)
        repo.create.return_value = created
        async with client as c:
            resp = await c.post("/api/v1/export/request")
        assert resp.status_code == 201
        body = resp.json()
        assert body["export_id"] == str(created.id)
        assert body["status"] == "pending"
        assert "created_at" in body
        repo.create.assert_awaited_once_with(user.id, COMMUNITY_ID)
        enqueue.assert_called_once_with(created.id)
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"export_request:{user.id}:{day}"
        assert valkey.store[key] == 1
        assert valkey.ttl[key] == 86400

    async def test_rate_limit_enforced(self, client, user, repo, enqueue):
        repo.create.return_value = _export(user.id)
        async with client as c:
            first = await c.post("/api/v1/export/request")
            second = await c.post("/api/v1/export/request")
        assert first.status_code == 201
        assert second.status_code == 429
        err = second.json()["error"]
        assert err["code"] == "RATE_LIMITED"
        assert err["message"] == "You can request one export per day"
        assert repo.create.await_count == 1
        assert enqueue.call_count == 1


class TestExportStatus:
    async def test_status_ready_has_download_url(self, client, user, repo):
        now = datetime.now(UTC)
        exp = _export(
            user.id,
            status="ready",
            ready_at=now,
            expires_at=now + timedelta(hours=48),
            file_size_bytes=1234,
        )
        repo.get_by_id.return_value = exp
        async with client as c:
            resp = await c.get(f"/api/v1/export/{exp.id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["export_id"] == str(exp.id)
        assert body["status"] == "ready"
        assert body["file_size_bytes"] == 1234
        assert body["download_url"] == f"/api/v1/export/{exp.id}/download"
        repo.get_by_id.assert_awaited_once_with(exp.id, COMMUNITY_ID)

    async def test_status_pending_has_no_download_url(self, client, user, repo):
        exp = _export(user.id)
        repo.get_by_id.return_value = exp
        async with client as c:
            resp = await c.get(f"/api/v1/export/{exp.id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert resp.json()["download_url"] is None

    async def test_expired_export_returns_no_download_url(self, client, user, repo):
        past = datetime.now(UTC) - timedelta(hours=50)
        exp = _export(user.id, status="ready", ready_at=past, expires_at=past + timedelta(hours=48))
        repo.get_by_id.return_value = exp
        async with client as c:
            resp = await c.get(f"/api/v1/export/{exp.id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "expired"
        assert resp.json()["download_url"] is None

    async def test_status_not_found(self, client, repo):
        repo.get_by_id.return_value = None
        async with client as c:
            resp = await c.get(f"/api/v1/export/{uuid.uuid4()}/status")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    async def test_status_other_users_export_forbidden(self, client, repo):
        repo.get_by_id.return_value = _export(uuid.uuid4())
        async with client as c:
            resp = await c.get(f"/api/v1/export/{uuid.uuid4()}/status")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "AUTHORIZATION_ERROR"


def test_build_service_wires_dependencies():
    settings = MagicMock(COMMUNITY_ID=str(COMMUNITY_ID))
    svc = export._build_service(AsyncMock(), settings, FakeValkey())
    assert isinstance(svc, ExportService)


def test_enqueue_sends_named_task(monkeypatch):
    sent = MagicMock()
    monkeypatch.setattr(export.celery_app, "send_task", sent)
    eid = uuid.uuid4()
    export.enqueue_export(eid)
    sent.assert_called_once_with("app.tasks.export_tasks.generate_user_export", args=[str(eid)])
