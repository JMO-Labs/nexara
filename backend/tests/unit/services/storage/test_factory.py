"""
@file test_factory.py
@brief Unit tests for the storage backend factory.

Verifies that the factory returns the correct backend type based on
settings and raises on unknown backend names.
"""

import pytest

from app.core.config import Settings
from app.services.storage.base import StorageError
from app.services.storage.factory import get_storage_backend, reset_storage_backend
from app.services.storage.local import LocalStorageBackend
from app.services.storage.s3 import S3StorageBackend


@pytest.fixture(autouse=True)
def _reset_singleton():
    """@brief Reset the factory singleton before and after each test."""
    reset_storage_backend()
    yield
    reset_storage_backend()


class TestFactory:
    """@brief Verify factory behaviour for each backend type."""

    def test_local_backend(self):
        settings = Settings(SECRET_KEY="test", STORAGE_BACKEND="local")
        backend = get_storage_backend(settings)
        assert isinstance(backend, LocalStorageBackend)

    def test_s3_backend(self):
        settings = Settings(
            SECRET_KEY="test",
            STORAGE_BACKEND="s3",
            S3_ENDPOINT_URL="http://garage:3900",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="test-bucket",
        )
        backend = get_storage_backend(settings)
        assert isinstance(backend, S3StorageBackend)

    def test_unknown_backend_raises(self):
        settings = Settings(SECRET_KEY="test", STORAGE_BACKEND="gcs")
        with pytest.raises(StorageError, match="Unknown storage backend"):
            get_storage_backend(settings)

    def test_case_insensitive(self):
        settings = Settings(SECRET_KEY="test", STORAGE_BACKEND="LOCAL")
        backend = get_storage_backend(settings)
        assert isinstance(backend, LocalStorageBackend)

    def test_singleton_returns_same_instance(self):
        settings = Settings(SECRET_KEY="test", STORAGE_BACKEND="local")
        first = get_storage_backend(settings)
        second = get_storage_backend(settings)
        assert first is second

    def test_reset_clears_singleton(self):
        settings = Settings(SECRET_KEY="test", STORAGE_BACKEND="local")
        first = get_storage_backend(settings)
        reset_storage_backend()
        second = get_storage_backend(settings)
        assert first is not second
