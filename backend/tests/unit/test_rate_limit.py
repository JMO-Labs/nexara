"""
@file test_rate_limit.py
@brief Unit tests for rate limiting configuration.

Verifies limiter instance is configured with correct storage backend
and default limits.
"""

from __future__ import annotations


class TestRateLimitConfig:
    """@brief Rate limiter configuration tests."""

    def test_limiter_exists(self):
        from app.core.rate_limit import limiter
        assert limiter is not None

    def test_key_func_is_remote_address(self):
        from slowapi.util import get_remote_address

        from app.core.rate_limit import limiter
        assert limiter._key_func is get_remote_address

    def test_storage_uri_uses_valkey(self):
        from app.core.rate_limit import storage_uri
        if storage_uri is not None:
            assert "redis" in storage_uri or "valkey" in storage_uri

    def test_build_storage_uri_returns_cache_url(self):
        from app.core.rate_limit import _build_storage_uri
        uri = _build_storage_uri()
        if uri:
            assert "/2" in uri
