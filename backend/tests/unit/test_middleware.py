"""
@file test_middleware.py
@brief Unit tests for HTTP middleware stack.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.middleware import (
    CloudflareRealIPMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)


@pytest.fixture
def _base_app() -> FastAPI:
    """@brief Minimal FastAPI app for middleware testing."""
    test_app = FastAPI()

    @test_app.get("/echo")
    async def echo():
        return {"ok": True}

    return test_app


class TestRequestIDMiddleware:
    """@brief Verify request ID generation and propagation."""

    def test_generates_request_id(self, _base_app):
        _base_app.add_middleware(RequestIDMiddleware)
        client = TestClient(_base_app)
        resp = client.get("/echo")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 36

    def test_preserves_existing_request_id(self, _base_app):
        _base_app.add_middleware(RequestIDMiddleware)
        client = TestClient(_base_app)
        resp = client.get("/echo", headers={"X-Request-ID": "my-custom-id"})
        assert resp.headers["X-Request-ID"] == "my-custom-id"


class TestSecurityHeadersMiddleware:
    """@brief Verify security headers are added to every response."""

    def test_security_headers_present(self, _base_app):
        _base_app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(_base_app)
        resp = client.get("/echo")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in resp.headers


class TestStructuredLoggingMiddleware:
    """@brief Verify logging middleware does not break responses."""

    def test_response_unmodified(self, _base_app):
        _base_app.add_middleware(StructuredLoggingMiddleware)
        client = TestClient(_base_app)
        resp = client.get("/echo")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestCloudflareRealIPMiddleware:
    """@brief Verify CF-Connecting-IP header is respected when enabled."""

    def test_replaces_client_ip_when_enabled(self):
        from starlette.requests import Request as StarletteRequest

        settings = Settings(CF_ACCESS_ENABLED=True, SECRET_KEY="test")
        test_app = FastAPI()
        test_app.add_middleware(CloudflareRealIPMiddleware, settings=settings)

        @test_app.get("/ip")
        async def get_ip(request: StarletteRequest):
            return {"ip": request.client.host if request.client else "none"}

        client = TestClient(test_app)
        resp = client.get("/ip", headers={"CF-Connecting-IP": "1.2.3.4"})
        assert resp.json()["ip"] == "1.2.3.4"

    def test_no_replacement_when_disabled(self):
        from starlette.requests import Request as StarletteRequest

        settings = Settings(CF_ACCESS_ENABLED=False, SECRET_KEY="test")
        test_app = FastAPI()
        test_app.add_middleware(CloudflareRealIPMiddleware, settings=settings)

        @test_app.get("/ip")
        async def get_ip(request: StarletteRequest):
            return {"ip": request.client.host if request.client else "none"}

        client = TestClient(test_app)
        resp = client.get("/ip", headers={"CF-Connecting-IP": "1.2.3.4"})
        assert resp.json()["ip"] != "1.2.3.4"
