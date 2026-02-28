"""
@file test_exceptions.py
@brief Unit tests for custom exception classes and handlers.
"""

import pytest
from starlette.testclient import TestClient

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    StorageError,
)


class TestExceptionClasses:
    """@brief Verify exception attributes are set correctly."""

    def test_app_error_defaults(self):
        exc = AppError()
        assert exc.code == "INTERNAL_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_app_error_custom(self):
        exc = AppError(code="CUSTOM", message="test msg", status_code=418, details={"a": 1})
        assert exc.code == "CUSTOM"
        assert exc.message == "test msg"
        assert exc.status_code == 418
        assert exc.details == {"a": 1}

    def test_authentication_error(self):
        exc = AuthenticationError()
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == 401

    def test_authorization_error(self):
        exc = AuthorizationError()
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403

    def test_not_found_error(self):
        exc = NotFoundError()
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404

    def test_conflict_error(self):
        exc = ConflictError()
        assert exc.code == "CONFLICT"
        assert exc.status_code == 409

    def test_rate_limit_error(self):
        exc = RateLimitError()
        assert exc.code == "RATE_LIMITED"
        assert exc.status_code == 429

    def test_storage_error(self):
        exc = StorageError()
        assert exc.code == "STORAGE_ERROR"
        assert exc.status_code == 503


class TestExceptionHandlers:
    """@brief Verify exception handlers produce correct JSON envelopes."""

    @pytest.fixture
    def client(self):
        """Create a minimal FastAPI app with exception handlers for testing."""
        from fastapi import FastAPI

        from app.core.exceptions import register_exception_handlers

        test_app = FastAPI()
        register_exception_handlers(test_app)

        @test_app.get("/auth-error")
        async def auth_error():
            raise AuthenticationError()

        @test_app.get("/not-found")
        async def not_found():
            raise NotFoundError(message="Item not found")

        @test_app.get("/unhandled")
        async def unhandled():
            raise RuntimeError("boom")

        return TestClient(test_app, raise_server_exceptions=False)

    def test_auth_error_handler(self, client):
        resp = client.get("/auth-error")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_not_found_handler(self, client):
        resp = client.get("/not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Item not found"

    def test_unhandled_exception_handler(self, client):
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
