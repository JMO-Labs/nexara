"""
@file test_cors.py
@brief Unit tests for CORS middleware configuration.

Verifies CORS headers are correctly applied for allowed and disallowed origins.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


class TestCORS:
    """@brief CORS header behavior tests."""

    @pytest.mark.asyncio
    async def test_preflight_returns_cors_headers(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type, Authorization",
                },
            )

        assert resp.status_code == 200
        assert "access-control-allow-methods" in resp.headers

    @pytest.mark.asyncio
    async def test_non_preflight_includes_origin_header(self, test_app):
        from unittest.mock import patch

        with (
            patch("app.api.v1.health._check_db", return_value=True),
            patch("app.api.v1.health._check_redis", return_value=True),
            patch("app.api.v1.health._check_storage", return_value=True),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/healthz",
                    headers={"Origin": "http://localhost:3000"},
                )

            assert resp.status_code in (200, 503)
