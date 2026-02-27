"""
@file test_waf.py
@brief Unit tests for the WAF middleware.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.waf import WAFMiddleware


@pytest.fixture
def waf_app() -> TestClient:
    """@brief FastAPI app with WAF enabled (no Valkey cache)."""
    settings = Settings(WAF_ENABLED=True, SECRET_KEY="test")
    app = FastAPI()
    app.add_middleware(WAFMiddleware, settings=settings, cache_client=None)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.post("/ok")
    async def ok_post():
        return {"status": "ok"}

    return TestClient(app)


@pytest.fixture
def waf_disabled_app() -> TestClient:
    """@brief FastAPI app with WAF disabled."""
    settings = Settings(WAF_ENABLED=False, SECRET_KEY="test")
    app = FastAPI()
    app.add_middleware(WAFMiddleware, settings=settings, cache_client=None)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    return TestClient(app)


class TestWAFBlocking:
    """@brief Verify WAF blocks common attack patterns."""

    def test_normal_request_passes(self, waf_app):
        resp = waf_app.get("/ok")
        assert resp.status_code == 200

    def test_sql_injection_in_query_blocked(self, waf_app):
        resp = waf_app.get("/ok?q=information_schema")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "BAD_REQUEST"

    def test_path_traversal_blocked(self, waf_app):
        resp = waf_app.get("/ok?file=../../etc/passwd")
        assert resp.status_code == 400

    def test_blocked_user_agent(self, waf_app):
        resp = waf_app.get("/ok", headers={"User-Agent": "sqlmap/1.5"})
        assert resp.status_code == 400

    def test_oversized_headers_blocked(self, waf_app):
        huge_header = "X" * 9000
        resp = waf_app.get("/ok", headers={"X-Big": huge_header})
        assert resp.status_code == 400

    def test_post_request_passes(self, waf_app):
        resp = waf_app.post("/ok")
        assert resp.status_code == 200


class TestWAFDisabled:
    """@brief Verify requests pass through when WAF is disabled."""

    def test_sql_injection_passes_when_disabled(self, waf_disabled_app):
        resp = waf_disabled_app.get("/ok?q=UNION SELECT")
        assert resp.status_code == 200

    def test_blocked_ua_passes_when_disabled(self, waf_disabled_app):
        resp = waf_disabled_app.get("/ok", headers={"User-Agent": "nikto"})
        assert resp.status_code == 200
