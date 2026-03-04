"""
@file conftest.py
@brief Shared fixtures for unit tests requiring the FastAPI app.

Provides a properly configured test app with mocked external dependencies
(Valkey, database) so that tests can run without live services.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from app.core.config import Settings, get_settings

_TEST_SETTINGS = Settings(
    SECRET_KEY="test-unit-secret",
    JWT_ALGORITHM="HS256",
    WAF_ENABLED=True,
    ENABLE_METRICS=False,
    DEBUG=True,
    JWT_PRIVATE_KEY_PATH="/tmp/nexara_test_jwt_private.pem",
    JWT_PUBLIC_KEY_PATH="/tmp/nexara_test_jwt_public.pem",
    ALLOWED_ORIGINS="http://localhost:3000",
)


@pytest.fixture
def test_app() -> FastAPI:
    """
    @brief Create a FastAPI app for unit tests with no external dependencies.

    Disables the lifespan (no Valkey/DB connections) and replaces the
    SlowAPI rate limiter with in-memory storage to avoid Valkey dependency.
    The Settings are overridden to use HS256 and writable paths.
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    memory_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000/minute"],
        storage_uri="memory://",
        strategy="fixed-window",
    )

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    def _test_settings():
        return _TEST_SETTINGS

    with (
        patch("app.core.rate_limit.limiter", memory_limiter),
        patch("app.main.limiter", memory_limiter),
        patch("app.main.lifespan", noop_lifespan),
        patch("app.main.get_settings", _test_settings),
    ):
        from app.main import create_app

        app = create_app()
        app.state.limiter = memory_limiter
        app.dependency_overrides[get_settings] = _test_settings

    return app
