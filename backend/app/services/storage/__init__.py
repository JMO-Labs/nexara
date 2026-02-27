"""
@file __init__.py
@brief Storage abstraction package.

Re-exports the public API: the protocol, exceptions, factory,
validation helpers, and quota enforcement.
"""

from app.services.storage.base import (
    StorageBackend,
    StorageError,
    StorageKeyNotFoundError,
)
from app.services.storage.factory import get_storage_backend, reset_storage_backend
from app.services.storage.quota import (
    QuotaExceededError,
    check_quota,
    decrement_storage_used,
    increment_storage_used,
    recalculate_storage_used,
)
from app.services.storage.validation import (
    UploadValidationError,
    validate_file_content,
    validate_file_size,
)

__all__ = [
    "QuotaExceededError",
    "StorageBackend",
    "StorageError",
    "StorageKeyNotFoundError",
    "UploadValidationError",
    "check_quota",
    "decrement_storage_used",
    "get_storage_backend",
    "increment_storage_used",
    "recalculate_storage_used",
    "reset_storage_backend",
    "validate_file_content",
    "validate_file_size",
]
