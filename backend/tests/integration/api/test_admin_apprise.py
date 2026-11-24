"""@file test_admin_apprise.py
@brief Integration tests for /api/v1/admin/apprise (targets, settings, roles).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.admin_apprise import _service
from app.core.dependencies import get_current_user
from app.services.admin_apprise_service import AdminAppriseService

CID = uuid.uuid4()


class FakeRepo:
    """@brief In-memory AppriseRepository stand-in."""

    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, SimpleNamespace] = {}
        self.local = False

    async def create(self, cid, user_id, url, label=None, is_admin_target=False):
        r = SimpleNamespace(
            id=uuid.uuid4(),
            community_id=cid,
            user_id=user_id,
            apprise_url=url,
            label=label,
            enabled=True,
            failure_count=0,
            last_failure_at=None,
            created_at="2026-01-01T00:00:00Z",
            is_admin_target=is_admin_target,
        )
        self.rows[r.id] = r
        return r

    async def get(self, i):
        return self.rows.get(i)

    async def list_admin_targets(self, cid, enabled_only=True):
        return [r for r in self.rows.values() if r.is_admin_target]

    async def delete(self, i):
        return self.rows.pop(i, None) is not None

    async def test_send(self, i, t, b):
        return True, "ok"

    async def allow_local(self, cid):
        return self.local

    async def set_allow_local(self, cid, v):
        self.local = v


@pytest.fixture
def env(test_app):
    repo, audit = FakeRepo(), MagicMock(append=AsyncMock())
    svc = AdminAppriseService(repo, CID, audit, uuid.uuid4(), "10.0.0.1")
    test_app.dependency_overrides[_service] = lambda: svc

    def client(role="admin"):
        user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
        test_app.dependency_overrides[get_current_user] = lambda: user
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield SimpleNamespace(client=client, repo=repo, audit=audit)
    test_app.dependency_overrides.clear()


async def test_create_local_target_ok_and_never_returns_url(env):
    async with env.client() as c:
        r = await c.post(
            "/api/v1/admin/apprise/targets", json={"apprise_url": "ntfy://192.168.1.10/topic"}
        )
        assert r.status_code == 201
        assert "192.168" not in r.text and "apprise_url" not in r.json()
        lst = await c.get("/api/v1/admin/apprise/targets")
    assert len(lst.json()) == 1
    assert env.audit.append.await_args.kwargs["action"] == "apprise.target.created"
    assert "192.168" not in str(env.audit.append.await_args)
    assert next(iter(env.repo.rows.values())).is_admin_target


async def test_invalid_url_400(env):
    async with env.client() as c:
        r = await c.post("/api/v1/admin/apprise/targets", json={"apprise_url": "nope"})
    assert r.status_code == 400


async def test_delete_test_and_settings(env):
    async with env.client() as c:
        tid = (
            await c.post(
                "/api/v1/admin/apprise/targets", json={"apprise_url": "ntfy://192.168.1.10/t"}
            )
        ).json()["id"]
        assert (await c.post(f"/api/v1/admin/apprise/targets/{tid}/test")).json()[
            "status"
        ] == "sent"
        assert (
            await c.put("/api/v1/admin/apprise/settings", json={"allow_local": True})
        ).json() == {"allow_local": True}
        assert env.repo.local is True
        assert (await c.delete(f"/api/v1/admin/apprise/targets/{tid}")).status_code == 200
        assert (await c.delete(f"/api/v1/admin/apprise/targets/{tid}")).status_code == 404


async def test_member_forbidden(env):
    async with env.client(role="member") as c:
        r = await c.post("/api/v1/admin/apprise/targets", json={"apprise_url": "ntfy://x/t"})
        s = await c.put("/api/v1/admin/apprise/settings", json={"allow_local": True})
    assert r.status_code == 403 and s.status_code == 403
    assert not env.repo.rows
