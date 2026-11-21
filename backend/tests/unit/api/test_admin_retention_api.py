"""
@file test_admin_retention_api.py
@brief Unit tests for admin retention endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.schemas.admin_retention import RetentionPolicyOut

BASE = "/api/v1/admin/retention"
BODY = {"enabled": True, "retention_days": 14, "delete_media_files": False}


def _out(key="notifications", days=14):
    return RetentionPolicyOut(
        policy_key=key,
        enabled=True,
        retention_days=days,
        delete_media_files=False,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_by=None,
    )


@pytest.fixture
def svc(test_app):
    from app.api.v1 import admin_retention as mod

    s = AsyncMock()
    test_app.dependency_overrides[mod._build_service] = lambda: s
    yield s
    test_app.dependency_overrides.pop(mod._build_service, None)


def _login(test_app, role):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role

    async def _u():
        return user

    test_app.dependency_overrides[get_current_user] = _u
    return user


@pytest.fixture(autouse=True)
def _cleanup(test_app):
    yield
    test_app.dependency_overrides.pop(get_current_user, None)


async def _req(test_app, method, url, **kw):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, url, **kw)


async def test_list_unauthenticated(test_app, svc):
    assert (await _req(test_app, "GET", BASE)).status_code == 401


async def test_list_member_forbidden(test_app, svc):
    _login(test_app, "member")
    assert (await _req(test_app, "GET", BASE)).status_code == 403


async def test_put_member_forbidden(test_app, svc):
    _login(test_app, "member")
    assert (await _req(test_app, "PUT", f"{BASE}/notifications", json=BODY)).status_code == 403


async def test_list_admin_ok(test_app, svc):
    _login(test_app, "admin")
    svc.list_policies.return_value = [_out()]
    r = await _req(test_app, "GET", BASE)
    assert r.status_code == 200
    assert r.json()[0]["policy_key"] == "notifications"


async def test_put_updates(test_app, svc):
    user = _login(test_app, "admin")
    svc.update.return_value = _out()
    r = await _req(test_app, "PUT", f"{BASE}/notifications", json=BODY)
    assert r.status_code == 200
    assert r.json()["retention_days"] == 14
    args = svc.update.call_args.args
    assert args[0] == "notifications"
    assert args[2] == user.id


async def test_put_null_days_allowed(test_app, svc):
    _login(test_app, "admin")
    svc.update.return_value = _out(days=None)
    r = await _req(test_app, "PUT", f"{BASE}/post_age", json={**BODY, "retention_days": None})
    assert r.status_code == 200


async def test_put_unknown_key_404(test_app, svc):
    _login(test_app, "admin")
    svc.update.side_effect = NotFoundError("nope")
    r = await _req(test_app, "PUT", f"{BASE}/bogus", json=BODY)
    assert r.status_code == 404


@pytest.mark.parametrize(
    "bad", [{**BODY, "retention_days": 0}, {"enabled": True}, {**BODY, "enabled": "x"}]
)
async def test_put_invalid_body_422(test_app, svc, bad):
    _login(test_app, "admin")
    r = await _req(test_app, "PUT", f"{BASE}/notifications", json=bad)
    assert r.status_code == 422
