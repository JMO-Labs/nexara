"""
@file test_auth_2fa.py
@brief Integration tests for /api/v1/auth/2fa/* and /api/v1/admin/security routes.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.deps_two_factor import get_admin_security_service, get_two_factor_service
from app.services.admin_security_service import AdminSecurityService

CID = uuid.uuid4()


def _client(app, role="member", svc=None, admin_svc=None):
    user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=CID)
    app.dependency_overrides[get_current_user] = lambda: user
    if svc is not None:
        app.dependency_overrides[get_two_factor_service] = lambda: svc
    if admin_svc is not None:
        app.dependency_overrides[get_admin_security_service] = lambda: admin_svc
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _clear(test_app):
    yield
    test_app.dependency_overrides.clear()


async def test_routes_delegate_and_shape(test_app):
    svc = MagicMock(
        start=AsyncMock(return_value={"secret": "S", "otpauth_uri": "otpauth://x"}),
        confirm=AsyncMock(return_value=["c"] * 10),
        regenerate=AsyncMock(return_value=["d"] * 10),
        disable=AsyncMock(),
        status=AsyncMock(
            return_value={
                "totp": True,
                "passkeys": 1,
                "recovery_left": 9,
                "required": False,
                "grace_until": None,
            }
        ),
    )
    async with _client(test_app, svc=svc) as c:
        assert (await c.post("/api/v1/auth/2fa/totp/start")).json()["secret"] == "S"
        r = await c.post("/api/v1/auth/2fa/totp/confirm", json={"code": "123456"})
        assert len(r.json()["recovery_codes"]) == 10
        r = await c.post("/api/v1/auth/2fa/recovery/regenerate", json={"code": "123456"})
        assert len(r.json()["recovery_codes"]) == 10
        assert (
            await c.post("/api/v1/auth/2fa/totp/disable", json={"password": "p"})
        ).status_code == 200
        st = (await c.get("/api/v1/auth/2fa/status")).json()
        assert st == {
            "totp": True,
            "passkeys": 1,
            "recovery_left": 9,
            "required": False,
            "grace_until": None,
        }
        # legacy aliases
        assert (await c.post("/api/v1/auth/2fa/enroll")).status_code == 200
        r = await c.post("/api/v1/auth/2fa/verify", json={"code": "123456"})
        assert len(r.json()["backup_codes"]) == 10
    svc.disable.assert_awaited_once_with("p", None)


async def test_admin_reset_and_policy(test_app):
    users, repo, audit = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get_policy.return_value = "off"
    svc = AdminSecurityService(users, repo, audit, CID, uuid.uuid4(), None)
    target = uuid.uuid4()
    async with _client(test_app, "admin", admin_svc=svc) as c:
        assert (await c.post(f"/api/v1/admin/users/{target}/reset-2fa")).status_code == 200
        assert (await c.put("/api/v1/admin/security", json={"require_2fa": "everyone"})).json() == {
            "require_2fa": "everyone"
        }
        assert (
            await c.put("/api/v1/admin/security", json={"require_2fa": "bad"})
        ).status_code == 422
        assert (await c.get("/api/v1/admin/security")).json() == {"require_2fa": "off"}
    repo.delete_passkeys.assert_awaited_once_with(target, CID)
    repo.set_policy.assert_awaited_once_with(CID, "everyone")


async def test_admin_routes_forbidden_for_member(test_app):
    svc = MagicMock(reset_2fa=AsyncMock(), set_policy=AsyncMock())
    async with _client(test_app, "member", admin_svc=svc) as c:
        r1 = await c.post(f"/api/v1/admin/users/{uuid.uuid4()}/reset-2fa")
        r2 = await c.put("/api/v1/admin/security", json={"require_2fa": "off"})
    assert r1.status_code == 403 and r2.status_code == 403
    svc.reset_2fa.assert_not_called()
