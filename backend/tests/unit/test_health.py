"""
@file test_health.py
@brief Unit tests for the /healthz endpoint with mocked component checks.

Validates that the health endpoint returns correct status codes and
payloads when components are healthy or degraded.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestHealthEndpoint:
    """@brief Health check endpoint behavior tests."""

    @pytest.mark.asyncio
    async def test_healthy_returns_200(self, test_app):
        with (
            patch("app.api.v1.health._check_db", return_value=True),
            patch("app.api.v1.health._check_redis", return_value=True),
            patch("app.api.v1.health._check_storage", return_value=True),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/healthz")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["checks"]["db"] is True
            assert data["checks"]["redis"] is True
            assert "version" in data

    @pytest.mark.asyncio
    async def test_degraded_returns_503_when_db_down(self, test_app):
        with (
            patch("app.api.v1.health._check_db", return_value=False),
            patch("app.api.v1.health._check_redis", return_value=True),
            patch("app.api.v1.health._check_storage", return_value=True),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/healthz")

            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["checks"]["db"] is False

    @pytest.mark.asyncio
    async def test_degraded_returns_503_when_redis_down(self, test_app):
        with (
            patch("app.api.v1.health._check_db", return_value=True),
            patch("app.api.v1.health._check_redis", return_value=False),
            patch("app.api.v1.health._check_storage", return_value=True),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/healthz")

            assert resp.status_code == 503
            data = resp.json()
            assert data["checks"]["redis"] is False

    @pytest.mark.asyncio
    async def test_storage_non_critical(self, test_app):
        with (
            patch("app.api.v1.health._check_db", return_value=True),
            patch("app.api.v1.health._check_redis", return_value=True),
            patch("app.api.v1.health._check_storage", return_value=False),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/healthz")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["checks"]["storage"] is False
