"""
@file test_features_api.py
@brief API tests for feature flag routes and the users/me timezone field.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.core.deps_age import get_community
from app.core.features import FEATURE_DEFAULTS


@pytest.fixture
def svc(test_app):
    from app.api.v1 import features as mod

    s = MagicMock()
    state = dict(FEATURE_DEFAULTS)

    async def _get():
        return dict(state)

    async def _update(patch):
        state.update(patch)
        return dict(state)

    s.get = AsyncMock(side_effect=_get)
    s.update = AsyncMock(side_effect=_update)
    test_app.dependency_overrides[mod.get_features_service] = lambda: s
    yield s
    test_app.dependency_overrides.pop(mod.get_features_service, None)


def _login(test_app, role):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[get_community] = lambda: None
    return user


@pytest.fixture(autouse=True)
def _cleanup(test_app):
    yield
    test_app.dependency_overrides.pop(get_current_user, None)
    test_app.dependency_overrides.pop(get_community, None)


async def _req(test_app, method, url, **kw):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, url, **kw)


async def test_member_can_read(test_app, svc):
    _login(test_app, "member")
    r = await _req(test_app, "GET", "/api/v1/features")
    assert r.status_code == 200
    assert r.json()["recipes"] is True


async def test_member_put_forbidden(test_app, svc):
    _login(test_app, "member")
    r = await _req(test_app, "PUT", "/api/v1/admin/features", json={"recipes": False})
    assert r.status_code == 403


async def test_admin_put_then_get(test_app, svc):
    _login(test_app, "admin")
    r = await _req(test_app, "PUT", "/api/v1/admin/features", json={"recipes": False})
    assert r.status_code == 200
    r = await _req(test_app, "GET", "/api/v1/admin/features")
    assert r.json()["recipes"] is False


async def test_admin_put_unknown_key_422(test_app, svc):
    _login(test_app, "admin")
    r = await _req(test_app, "PUT", "/api/v1/admin/features", json={"bogus": True})
    assert r.status_code == 422


async def test_patch_me_timezone_invalid_422(test_app):
    _login(test_app, "member")
    r = await _req(test_app, "PATCH", "/api/v1/users/me", json={"timezone": "Mars/Base"})
    assert r.status_code == 422


def test_timezone_schema_accepts_valid():
    from app.schemas.user import UserUpdateRequest

    assert UserUpdateRequest(timezone="America/Phoenix").timezone == "America/Phoenix"
