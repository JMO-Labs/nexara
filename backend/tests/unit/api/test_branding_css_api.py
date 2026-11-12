"""
@file test_branding_css_api.py
@brief Route test: PUT /api/v1/branding/ rejects bad custom CSS with 400.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def admin_override(test_app):
    """@brief Override get_current_user to return an admin."""
    from app.core.dependencies import get_current_user

    async def _override():
        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = "admin"
        return user

    test_app.dependency_overrides[get_current_user] = _override
    yield
    test_app.dependency_overrides.pop(get_current_user, None)


async def _put(test_app, css: str):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        return await c.put("/api/v1/branding/", json={"custom_css": css})


@pytest.mark.asyncio
async def test_put_oversized_css_returns_400(test_app, admin_override):
    resp = await _put(test_app, "a{}" * 5000)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "css_too_large"


@pytest.mark.asyncio
async def test_put_escaped_css_returns_400(test_app, admin_override):
    resp = await _put(test_app, "@\\69mport url(x);a{}")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "css_invalid"
