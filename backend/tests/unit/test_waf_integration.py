"""
@file test_waf_integration.py
@brief Integration-style tests for WAF middleware against the live app.

These tests send actual HTTP requests through the full middleware stack
and verify WAF blocking behavior at the application level.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


class TestWAFIntegration:
    """@brief WAF blocking behavior through the application stack."""

    @pytest.mark.asyncio
    async def test_sql_injection_blocked(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz?q=information_schema")

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz?file=../../etc/passwd")

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_blocked_user_agent(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/healthz",
                headers={"User-Agent": "sqlmap/1.0"},
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_clean_request_passes(self, test_app):
        from unittest.mock import patch

        with (
            patch("app.api.v1.health._check_db", return_value=True),
            patch("app.api.v1.health._check_redis", return_value=True),
            patch("app.api.v1.health._check_storage", return_value=True),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/healthz")

            assert resp.status_code == 200
