"""
@file __init__.py
@brief Storage abstraction package.

Re-exports the public API: the protocol, exceptions, factory,
and validation helpers.
"""

from app.services.storage.base import (
    StorageBackend,
    StorageError,
    StorageKeyNotFoundError,
)
from app.services.storage.factory import get_storage_backend, reset_storage_backend
from app.services.storage.validation import (
    UploadValidationError,
    validate_file_content,
    validate_file_size,
)

__all__ = [
    "StorageBackend",
    "StorageError",
    "StorageKeyNotFoundError",
    "UploadValidationError",
    "get_storage_backend",
    "reset_storage_backend",
    "validate_file_content",
    "validate_file_size",
]
