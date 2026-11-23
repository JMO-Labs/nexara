"""
@file test_admin_email.py
@brief Integration tests for /api/v1/admin/email (settings, test send, roles).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.dependencies import get_admin_email_service, get_current_user
from app.services.admin_email_service import AdminEmailService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
BODY = {
    "host": "smtp.gmail.com",
    "port": 587,
    "security": "starttls",
    "user": "me@gmail.com",
    "password": "abcd efgh ijkl mnop",
    "from_addr": "me@gmail.com",
}


class FakeRepo:
    """@brief In-memory CommunityRepository stand-in (smtp columns only)."""

    def __init__(self) -> None:
        self.row = SimpleNamespace(
            id=CID,
            smtp_host=None,
            smtp_port=None,
            smtp_security=None,
            smtp_user=None,
            smtp_password=None,
            smtp_from=None,
            smtp_from_name=None,
            smtp_auth="password",
            smtp_google_refresh=None,
            smtp_last_ok_at=None,
            smtp_last_error=None,
        )

    async def get(self, cid):
        return self.row if cid == CID else None

    async def update_smtp(self, cid, values):
        for k, v in values.items():
            setattr(self.row, k, v)
        return self.row


@pytest.fixture
def env(test_app):
    repo = FakeRepo()
    audit = MagicMock(append=AsyncMock())
    svc = AdminEmailService(repo, CID, Settings(), audit, uuid.uuid4(), "10.0.0.1")
    test_app.dependency_overrides[get_admin_email_service] = lambda: svc

    def client(role="admin"):
        user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: user
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, audit=audit)
    test_app.dependency_overrides.clear()


async def test_get_never_contains_password(env):
    async with env.client() as c:
        await c.put("/api/v1/admin/email", json=BODY)
        r = await c.get("/api/v1/admin/email")
    assert r.status_code == 200
    d = r.json()
    assert d["has_password"] is True and d["host"] == "smtp.gmail.com"
    assert "password" not in d and "abcd" not in r.text


async def test_put_audits(env):
    async with env.client() as c:
        r = await c.put("/api/v1/admin/email", json=BODY)
    assert r.status_code == 200
    assert env.audit.append.await_args.kwargs["action"] == "email.settings.updated"
    assert "abcd" not in str(env.audit.append.await_args)


async def test_non_admin_put_forbidden(env):
    async with env.client(role="member") as c:
        r = await c.put("/api/v1/admin/email", json=BODY)
    assert r.status_code == 403
    assert env.repo.row.smtp_host is None


async def test_bad_security_rejected(env):
    async with env.client() as c:
        r = await c.put("/api/v1/admin/email", json={"security": "plain"})
    assert r.status_code == 422


async def test_test_failure_returns_ok_false_and_stores_error(env):
    async with env.client() as c:
        await c.put("/api/v1/admin/email", json=BODY)
        with patch(
            "app.services.admin_email_service.send_email",
            AsyncMock(side_effect=OSError("535 bad credentials")),
        ):
            r = await c.post("/api/v1/admin/email/test", json={"to": "a@b.co"})
    assert r.status_code == 200
    assert r.json()["ok"] is False and "535" in r.json()["error"]
    assert "535" in env.repo.row.smtp_last_error
    assert "abcd" not in r.text


async def test_test_success(env):
    async with env.client() as c:
        await c.put("/api/v1/admin/email", json=BODY)
        with patch("app.services.admin_email_service.send_email", AsyncMock()):
            r = await c.post("/api/v1/admin/email/test", json={"to": "a@b.co"})
    assert r.json() == {"ok": True, "error": None}
    assert env.repo.row.smtp_last_ok_at is not None
