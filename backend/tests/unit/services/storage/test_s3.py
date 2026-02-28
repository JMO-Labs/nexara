"""
@file test_s3.py
@brief Unit tests for S3StorageBackend with mocked boto3 calls.

All S3 interactions are mocked via AsyncMock context managers.
No real S3/MinIO service is required.
"""

from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError

from app.services.storage.base import StorageError, StorageKeyNotFoundError
from app.services.storage.s3 import S3StorageBackend


@pytest.fixture
def backend():
    """@brief Create an S3StorageBackend with test credentials."""
    return S3StorageBackend(
        endpoint_url="http://garage:3900",
        access_key="test-key",
        secret_key="test-secret",
        bucket="nexara-test",
    )


def _make_client_error(code: str) -> ClientError:
    """@brief Helper to build a botocore ClientError with a given error code."""
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "test"}},
        operation_name="TestOp",
    )


class TestS3Put:
    """@brief Verify put() calls S3 with correct args."""

    async def test_calls_put_object(self, backend):
        mock_s3 = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            await backend.put("originals/test.jpg", b"data", "image/jpeg")

        mock_s3.put_object.assert_called_once_with(
            Bucket="nexara-test",
            Key="originals/test.jpg",
            Body=b"data",
            ContentType="image/jpeg",
        )

    async def test_wraps_client_error(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.put_object.side_effect = _make_client_error("AccessDenied")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            with pytest.raises(StorageError, match="S3 put failed"):
                await backend.put("key", b"data", "image/jpeg")


class TestS3Get:
    """@brief Verify get() reads the body stream correctly."""

    async def test_reads_body(self, backend):
        mock_body = AsyncMock()
        mock_body.read.return_value = b"file-bytes"
        mock_s3 = AsyncMock()
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            result = await backend.get("originals/test.jpg")

        assert result == b"file-bytes"
        mock_s3.get_object.assert_called_once_with(Bucket="nexara-test", Key="originals/test.jpg")

    async def test_raises_not_found_on_no_such_key(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.get_object.side_effect = _make_client_error("NoSuchKey")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            with pytest.raises(StorageKeyNotFoundError):
                await backend.get("missing/key")

    async def test_wraps_other_client_error(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.get_object.side_effect = _make_client_error("InternalError")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            with pytest.raises(StorageError, match="S3 get failed"):
                await backend.get("key")


class TestS3Delete:
    """@brief Verify delete() calls S3 correctly."""

    async def test_calls_delete_object(self, backend):
        mock_s3 = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            await backend.delete("originals/test.jpg")

        mock_s3.delete_object.assert_called_once_with(
            Bucket="nexara-test", Key="originals/test.jpg"
        )


class TestS3Exists:
    """@brief Verify exists() interprets head_object responses."""

    async def test_returns_true_when_present(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_object.return_value = {"ContentLength": 100}
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            assert await backend.exists("originals/test.jpg") is True

    async def test_returns_false_on_404(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_object.side_effect = _make_client_error("404")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            assert await backend.exists("missing/key") is False

    async def test_wraps_other_error(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_object.side_effect = _make_client_error("Forbidden")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            with pytest.raises(StorageError, match="S3 exists check failed"):
                await backend.exists("key")


class TestS3GetSize:
    """@brief Verify get_size() extracts ContentLength."""

    async def test_returns_content_length(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_object.return_value = {"ContentLength": 2048}
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            assert await backend.get_size("originals/test.jpg") == 2048

    async def test_raises_not_found_on_404(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_object.side_effect = _make_client_error("404")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            with pytest.raises(StorageKeyNotFoundError):
                await backend.get_size("missing/key")


class TestS3HealthCheck:
    """@brief Verify check_health() probes the bucket."""

    async def test_healthy(self, backend):
        mock_s3 = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            assert await backend.check_health() is True
        mock_s3.head_bucket.assert_called_once_with(Bucket="nexara-test")

    async def test_unhealthy(self, backend):
        mock_s3 = AsyncMock()
        mock_s3.head_bucket.side_effect = _make_client_error("403")
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_s3

        with patch.object(backend._session, "client", return_value=mock_ctx):
            assert await backend.check_health() is False
