"""
@file test_admin_ai_api.py
@brief Unit tests for the admin AI endpoints (config, metrics, test-connection).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.ai.admin_ai_service import AdminAIService

BASE = "/api/v1/admin/ai"


@pytest.fixture
def auth(test_app):
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "admin"

    async def _override():
        return user

    test_app.dependency_overrides[get_current_user] = _override
    yield user
    test_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def svc(test_app, auth):
    from app.core.dependencies import get_admin_ai_service

    mock = AsyncMock(spec=AdminAIService)
    test_app.dependency_overrides[get_admin_ai_service] = lambda: mock
    yield mock
    test_app.dependency_overrides.pop(get_admin_ai_service, None)


async def _call(test_app, method: str, path: str, **kw):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.request(method, f"{BASE}{path}", **kw)


@pytest.mark.asyncio
async def test_get_config(test_app, svc):
    svc.get_config.return_value = {"provider": "openai"}
    resp = await _call(test_app, "GET", "/config")
    assert resp.status_code == 200
    assert resp.json() == {"provider": "openai"}


@pytest.mark.asyncio
async def test_put_config_excludes_unset_fields(test_app, svc):
    svc.update_config.return_value = {"sass_level": 2}
    resp = await _call(test_app, "PUT", "/config", json={"sass_level": 2})
    assert resp.status_code == 200
    svc.update_config.assert_awaited_once_with({"sass_level": 2})


@pytest.mark.asyncio
async def test_put_config_rejects_out_of_range(test_app, svc):
    resp = await _call(test_app, "PUT", "/config", json={"sass_level": 9})
    assert resp.status_code == 422
    svc.update_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_metrics(test_app, svc):
    svc.get_metrics.return_value = {"daily_usage_cents": 3}
    resp = await _call(test_app, "GET", "/metrics")
    assert resp.status_code == 200
    assert resp.json()["daily_usage_cents"] == 3


@pytest.mark.asyncio
async def test_test_connection(test_app, svc):
    svc.test_connection.return_value = {"success": True, "message": "ok"}
    resp = await _call(test_app, "POST", "/test-connection")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_non_admin_forbidden(test_app, svc, auth):
    auth.role = "member"
    resp = await _call(test_app, "GET", "/config")
    assert resp.status_code == 403
    svc.get_config.assert_not_awaited()
