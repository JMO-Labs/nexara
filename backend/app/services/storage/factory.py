"""
@file factory.py
@brief Storage backend factory.

Resolves the active storage backend from application settings and
returns a singleton instance. Called once during application startup.
"""

from __future__ import annotations

import structlog

from app.core.config import Settings
from app.services.storage.base import StorageBackend, StorageError
from app.services.storage.local import LocalStorageBackend
from app.services.storage.s3 import S3StorageBackend

logger = structlog.get_logger(__name__)

_backend: StorageBackend | None = None


def get_storage_backend(settings: Settings) -> StorageBackend:
    """
    @brief Return the configured storage backend (singleton).

    Reads ``STORAGE_BACKEND`` from settings and instantiates the
    appropriate implementation. Subsequent calls return the same instance.

    @param settings Application settings.
    @return A :class:`StorageBackend` implementation.
    @raises StorageError If the backend name is unrecognized.
    """
    global _backend
    if _backend is not None:
        return _backend

    backend_name = settings.STORAGE_BACKEND.lower()

    if backend_name == "local":
        _backend = LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
        logger.info("storage_backend_init", backend="local", path=settings.LOCAL_STORAGE_PATH)
    elif backend_name == "s3":
        _backend = S3StorageBackend(
            endpoint_url=settings.S3_ENDPOINT_URL,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            bucket=settings.S3_BUCKET,
        )
        logger.info("storage_backend_init", backend="s3", bucket=settings.S3_BUCKET)
    else:
        raise StorageError(f"Unknown storage backend: {backend_name!r}")

    return _backend


def reset_storage_backend() -> None:
    """
    @brief Reset the singleton for testing purposes.

    Clears the cached backend so the next call to
    :func:`get_storage_backend` creates a fresh instance.
    """
    global _backend
    _backend = None
