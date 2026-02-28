"""
@file base.py
@brief StorageBackend protocol and custom exceptions.

Defines the contract that all storage implementations (local filesystem,
S3-compatible) must satisfy. The protocol is structural — implementations
do not need to inherit from it, only provide the same method signatures.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """
    @brief Abstract storage interface for media files.

    All storage keys are backend-generated UUID-based paths
    (e.g. ``originals/ab/cd/abcd1234-....jpg``). User input is never
    used directly as a key to prevent path traversal attacks.
    """

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """
        @brief Store data under the given key.

        @param key Storage key (UUID-based path).
        @param data Raw file bytes.
        @param content_type MIME type of the file.
        @raises StorageError On write failure.
        """
        ...

    async def get(self, key: str) -> bytes:
        """
        @brief Retrieve data for the given key.

        @param key Storage key.
        @return Raw file bytes.
        @raises StorageKeyNotFoundError If the key does not exist.
        @raises StorageError On read failure.
        """
        ...

    async def delete(self, key: str) -> None:
        """
        @brief Remove the object at the given key.

        No-op if the key does not exist.

        @param key Storage key.
        @raises StorageError On delete failure (other than missing key).
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        @brief Check whether the given key exists in storage.

        @param key Storage key.
        @return True if the key exists, False otherwise.
        """
        ...

    async def get_size(self, key: str) -> int:
        """
        @brief Return the size in bytes of the object at the given key.

        @param key Storage key.
        @return File size in bytes.
        @raises StorageKeyNotFoundError If the key does not exist.
        """
        ...

    async def check_health(self) -> bool:
        """
        @brief Verify that the storage backend is operational.

        @return True if healthy, False otherwise.
        """
        ...


class StorageError(Exception):
    """@brief Base exception for all storage operations."""


class StorageKeyNotFoundError(StorageError):
    """@brief Raised when a requested storage key does not exist."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Storage key not found: {key}")
