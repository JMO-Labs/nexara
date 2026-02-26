"""
@file test_config.py
@brief Unit tests for the application configuration module.
"""

from app.core.config import Settings, get_settings


class TestSettings:
    """@brief Verify Settings loads defaults and parses env vars correctly."""

    def test_default_app_name(self):
        """@brief Default APP_NAME should be 'Nexara'."""
        settings = Settings(
            SECRET_KEY="test-key",
            DATABASE_URL="postgresql+asyncpg://u:p@localhost/test",
        )
        assert settings.APP_NAME == "Nexara"

    def test_allowed_origins_empty(self):
        """@brief Empty ALLOWED_ORIGINS yields an empty list."""
        settings = Settings(
            SECRET_KEY="test-key",
            ALLOWED_ORIGINS="",
        )
        assert settings.allowed_origins_list == []

    def test_allowed_origins_parsed(self):
        """@brief Comma-separated ALLOWED_ORIGINS should split into a list."""
        settings = Settings(
            SECRET_KEY="test-key",
            ALLOWED_ORIGINS="https://a.com, https://b.com",
        )
        assert settings.allowed_origins_list == [
            "https://a.com",
            "https://b.com",
        ]

    def test_celery_broker_url(self):
        """@brief Celery broker URL should use Valkey DB 0."""
        settings = Settings(
            SECRET_KEY="test-key",
            REDIS_URL="redis://valkey:6379",
        )
        assert settings.celery_broker_url == "redis://valkey:6379/0"

    def test_redis_pubsub_url(self):
        """@brief Pub/Sub URL should use Valkey DB 1."""
        settings = Settings(
            SECRET_KEY="test-key",
            REDIS_URL="redis://valkey:6379",
        )
        assert settings.redis_pubsub_url == "redis://valkey:6379/1"

    def test_redis_cache_url(self):
        """@brief Cache URL should use Valkey DB 2."""
        settings = Settings(
            SECRET_KEY="test-key",
            REDIS_URL="redis://valkey:6379",
        )
        assert settings.redis_cache_url == "redis://valkey:6379/2"

    def test_default_storage_backend(self):
        """@brief Default storage backend should be 'local'."""
        settings = Settings(SECRET_KEY="test-key")
        assert settings.STORAGE_BACKEND == "local"

    def test_get_settings_returns_instance(self):
        """@brief get_settings() should return a Settings instance."""
        result = get_settings()
        assert isinstance(result, Settings)
