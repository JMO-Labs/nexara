"""
@file local.py
@brief Local filesystem storage backend.

Stores files under a configurable base directory with UUID-based sharding
to prevent any single directory from growing too large. The first four
characters of the key filename are used as a two-level directory prefix:
``ab/cd/abcd1234-....jpg``.
"""

from __future__ import annotations

import os
from pathlib import Path

import aiofiles
import structlog

from app.services.storage.base import StorageError, StorageKeyNotFoundError

logger = structlog.get_logger(__name__)


class LocalStorageBackend:
    """
    @brief Reads and writes files to a local directory.

    @param base_path Root directory for all stored files (e.g. ``/data/media``).
    """

    def __init__(self, base_path: str) -> None:
        self.base = Path(base_path)

    def _resolve(self, key: str) -> Path:
        """
        @brief Map a storage key to its absolute file path.

        Uses the filename portion of the key with a two-level shard prefix
        derived from the first four characters to distribute files across
        subdirectories.

        @param key Storage key (may include a logical prefix like ``originals/``).
        @return Absolute path on disk.
        @raises StorageError If the key is empty or invalid.
        """
        if not key or not key.strip():
            raise StorageError("Storage key must not be empty")

        parts = key.split("/")
        filename = parts[-1]
        prefix_dirs = parts[:-1]

        if len(filename) < 4:
            raise StorageError(f"Storage key filename too short: {filename}")

        shard = f"{filename[:2]}/{filename[2:4]}"
        return self.base.joinpath(*prefix_dirs, shard, filename)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """@brief Write file bytes to disk, creating parent directories as needed."""
        path = self._resolve(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "wb") as f:
                await f.write(data)
            logger.debug("storage_put", key=key, size=len(data))
        except OSError as exc:
            raise StorageError(f"Failed to write key {key}: {exc}") from exc

    async def get(self, key: str) -> bytes:
        """@brief Read file bytes from disk."""
        path = self._resolve(key)
        if not path.exists():
            raise StorageKeyNotFoundError(key)
        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except OSError as exc:
            raise StorageError(f"Failed to read key {key}: {exc}") from exc

    async def delete(self, key: str) -> None:
        """@brief Remove the file from disk. No-op if already missing."""
        path = self._resolve(key)
        try:
            if path.exists():
                path.unlink()
                logger.debug("storage_delete", key=key)
        except OSError as exc:
            raise StorageError(f"Failed to delete key {key}: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """@brief Check whether the file exists on disk."""
        return self._resolve(key).exists()

    async def get_size(self, key: str) -> int:
        """@brief Return the file size in bytes."""
        path = self._resolve(key)
        if not path.exists():
            raise StorageKeyNotFoundError(key)
        return path.stat().st_size

    async def check_health(self) -> bool:
        """@brief Verify the base directory exists and is writable."""
        try:
            if not self.base.exists():
                return False
            test_file = self.base / ".health_check"
            test_file.write_bytes(b"ok")
            test_file.unlink()
            return True
        except OSError:
            return False
