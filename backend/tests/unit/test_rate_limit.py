"""
@file test_rate_limit.py
@brief Unit tests for rate limiting configuration.

Verifies limiter instance is configured with correct storage backend
and default limits.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.testclient import TestClient

from app.core.rate_limit import rate_limit_key


class TestRateLimitConfig:
    """@brief Rate limiter configuration tests."""

    def test_limiter_exists(self):
        from app.core.rate_limit import limiter

        assert limiter is not None

    def test_key_func_is_real_client_ip(self):
        from app.core.rate_limit import limiter, rate_limit_key

        assert limiter._key_func is rate_limit_key


def _req(headers: dict[str, str], host: str | None = "127.0.0.1"):
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    return SimpleNamespace(
        headers=Headers(headers), client=SimpleNamespace(host=host) if host else None
    )


def test_rate_limit_key_uses_rightmost_forwarded_ip():
    from app.core.rate_limit import rate_limit_key

    assert rate_limit_key(_req({"x-forwarded-for": "6.6.6.6, 198.51.100.1"})) == "198.51.100.1"
    assert rate_limit_key(_req({})) == "127.0.0.1"
    assert rate_limit_key(_req({}, host=None)) == "unknown"


def test_different_clients_behind_proxy_get_separate_buckets():
    lim = Limiter(key_func=rate_limit_key, storage_uri="memory://")
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/x")
    @lim.limit("1/minute")
    async def x(request: Request) -> dict[str, bool]:
        return {"ok": True}

    c = TestClient(app, client=("127.0.0.1", 50000))
    a = {"X-Forwarded-For": "198.51.100.1"}
    b = {"X-Forwarded-For": "198.51.100.2"}
    assert c.get("/x", headers=a).status_code == 200
    assert c.get("/x", headers=b).status_code == 200
    assert c.get("/x", headers=a).status_code == 429

    def test_storage_uri_uses_valkey(self):
        from app.core.rate_limit import storage_uri

        if storage_uri is not None:
            assert "redis" in storage_uri or "valkey" in storage_uri

    def test_build_storage_uri_returns_cache_url(self):
        from app.core.rate_limit import _build_storage_uri

        uri = _build_storage_uri()
        if uri:
            assert "/2" in uri
