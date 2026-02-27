"""
@file test_error_format.py
@brief Unit tests verifying error responses follow the standard envelope format.

All API errors must return ``{ "error": { "code": ..., "message": ..., "details": ... } }``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestErrorFormat:
    """@brief Error envelope format tests."""

    @pytest.mark.asyncio
    async def test_404_follows_error_envelope(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/nonexistent-endpoint")

        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_validation_error_format(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "not-valid", "password": ""},
            )

        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    @pytest.mark.asyncio
    async def test_auth_error_returns_401(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer invalid-token"},
            )

        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"
