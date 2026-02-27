"""
@file test_local.py
@brief Unit tests for LocalStorageBackend.

Uses a temporary directory to verify file CRUD operations,
path resolution with shard prefixes, and health checks.
"""

import pytest

from app.services.storage.base import StorageError, StorageKeyNotFoundError
from app.services.storage.local import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    """@brief Create a LocalStorageBackend rooted at a temp directory."""
    return LocalStorageBackend(str(tmp_path))


class TestLocalPut:
    """@brief Verify put() creates files at the expected shard path."""

    async def test_creates_file(self, storage, tmp_path):
        key = "originals/abcd1234-test.jpg"
        await storage.put(key, b"jpeg-data", "image/jpeg")

        expected = tmp_path / "originals" / "ab" / "cd" / "abcd1234-test.jpg"
        assert expected.exists()
        assert expected.read_bytes() == b"jpeg-data"

    async def test_creates_parent_dirs(self, storage, tmp_path):
        key = "thumbnails/ef012345-thumb.webp"
        await storage.put(key, b"webp-data", "image/webp")

        expected = tmp_path / "thumbnails" / "ef" / "01" / "ef012345-thumb.webp"
        assert expected.exists()

    async def test_overwrites_existing(self, storage):
        key = "originals/abcd1234-test.jpg"
        await storage.put(key, b"first", "image/jpeg")
        await storage.put(key, b"second", "image/jpeg")

        data = await storage.get(key)
        assert data == b"second"


class TestLocalGet:
    """@brief Verify get() returns correct bytes or raises on missing key."""

    async def test_returns_correct_bytes(self, storage):
        key = "originals/abcd1234-test.jpg"
        await storage.put(key, b"hello-world", "image/jpeg")

        data = await storage.get(key)
        assert data == b"hello-world"

    async def test_raises_on_missing_key(self, storage):
        with pytest.raises(StorageKeyNotFoundError) as exc_info:
            await storage.get("originals/missing1234-file.jpg")
        assert "missing1234-file.jpg" in str(exc_info.value)


class TestLocalDelete:
    """@brief Verify delete() removes files and is a no-op when missing."""

    async def test_removes_file(self, storage):
        key = "originals/abcd1234-test.jpg"
        await storage.put(key, b"data", "image/jpeg")
        assert await storage.exists(key) is True

        await storage.delete(key)
        assert await storage.exists(key) is False

    async def test_noop_when_missing(self, storage):
        await storage.delete("originals/nonexist1-file.jpg")


class TestLocalExists:
    """@brief Verify exists() returns correct boolean."""

    async def test_true_for_existing(self, storage):
        key = "originals/abcd1234-test.jpg"
        await storage.put(key, b"data", "image/jpeg")
        assert await storage.exists(key) is True

    async def test_false_for_missing(self, storage):
        assert await storage.exists("originals/nope1234-file.jpg") is False


class TestLocalGetSize:
    """@brief Verify get_size() returns correct byte count."""

    async def test_returns_size(self, storage):
        key = "originals/abcd1234-test.jpg"
        data = b"x" * 1024
        await storage.put(key, data, "image/jpeg")
        assert await storage.get_size(key) == 1024

    async def test_raises_on_missing(self, storage):
        with pytest.raises(StorageKeyNotFoundError):
            await storage.get_size("originals/gone1234-file.jpg")


class TestLocalHealthCheck:
    """@brief Verify check_health() validates directory writability."""

    async def test_healthy_directory(self, storage):
        assert await storage.check_health() is True

    async def test_unhealthy_missing_directory(self):
        backend = LocalStorageBackend("/nonexistent/path/that/does/not/exist")
        assert await backend.check_health() is False


class TestLocalResolve:
    """@brief Verify _resolve() path safety."""

    def test_empty_key_raises(self, storage):
        with pytest.raises(StorageError, match="must not be empty"):
            storage._resolve("")

    def test_short_filename_raises(self, storage):
        with pytest.raises(StorageError, match="too short"):
            storage._resolve("ab")
