"""
@file test_local_integration.py
@brief Integration tests for LocalStorageBackend on a real filesystem.

Uses pytest's tmp_path fixture for an isolated temporary directory.
These tests exercise the full put -> get -> exists -> get_size -> delete
lifecycle against real I/O.
"""

import pytest

from app.services.storage.base import StorageKeyNotFoundError
from app.services.storage.local import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    """@brief Create a LocalStorageBackend rooted at a temp directory."""
    return LocalStorageBackend(str(tmp_path))


class TestFullLifecycle:
    """@brief Verify a complete put -> get -> exists -> get_size -> delete cycle."""

    async def test_image_lifecycle(self, storage):
        key = "originals/a1b2c3d4-photo.jpg"
        data = b"\xff\xd8\xff" + b"\x00" * 1024

        await storage.put(key, data, "image/jpeg")
        assert await storage.exists(key) is True
        assert await storage.get_size(key) == len(data)

        retrieved = await storage.get(key)
        assert retrieved == data

        await storage.delete(key)
        assert await storage.exists(key) is False

    async def test_large_file(self, storage):
        """@brief Verify storage handles files up to several MB."""
        key = "originals/deadbeef-large.png"
        data = b"\x89PNG\r\n\x1a\n" + (b"x" * (2 * 1024 * 1024))

        await storage.put(key, data, "image/png")
        retrieved = await storage.get(key)
        assert len(retrieved) == len(data)
        assert retrieved == data

        await storage.delete(key)


class TestHealthCheck:
    """@brief Verify check_health against real directories."""

    async def test_valid_writable_directory(self, storage):
        assert await storage.check_health() is True

    async def test_nonexistent_directory(self):
        backend = LocalStorageBackend("/tmp/nexara-test-nonexistent-abc123")
        assert await backend.check_health() is False


class TestShardIsolation:
    """@brief Verify that files with different prefixes land in different shard dirs."""

    async def test_different_shards(self, storage, tmp_path):
        key1 = "originals/aaaa1111-one.jpg"
        key2 = "originals/bbbb2222-two.jpg"

        await storage.put(key1, b"one", "image/jpeg")
        await storage.put(key2, b"two", "image/jpeg")

        path1 = tmp_path / "originals" / "aa" / "aa" / "aaaa1111-one.jpg"
        path2 = tmp_path / "originals" / "bb" / "bb" / "bbbb2222-two.jpg"

        assert path1.exists()
        assert path2.exists()
        assert path1.parent != path2.parent


class TestDeleteIdempotency:
    """@brief Verify delete is safe to call multiple times."""

    async def test_double_delete(self, storage):
        key = "originals/abcd5678-item.jpg"
        await storage.put(key, b"data", "image/jpeg")
        await storage.delete(key)
        await storage.delete(key)

    async def test_get_after_delete_raises(self, storage):
        key = "originals/abcd5678-item.jpg"
        await storage.put(key, b"data", "image/jpeg")
        await storage.delete(key)

        with pytest.raises(StorageKeyNotFoundError):
            await storage.get(key)
