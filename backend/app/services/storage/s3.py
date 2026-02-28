"""
@file s3.py
@brief S3-compatible storage backend.

Works with any S3-compatible service: AWS S3, Garage, MinIO,
Backblaze B2, Cloudflare R2, Wasabi, DigitalOcean Spaces.
Uses ``aioboto3`` for fully async operations.
"""

from __future__ import annotations

from typing import Any, cast

import aioboto3
import structlog
from botocore.exceptions import ClientError

from app.services.storage.base import StorageError, StorageKeyNotFoundError

logger = structlog.get_logger(__name__)


class S3StorageBackend:
    """
    @brief Reads and writes objects to an S3-compatible bucket.

    @param endpoint_url S3 endpoint (e.g. ``http://garage:3900``).
    @param access_key AWS/S3 access key ID.
    @param secret_key AWS/S3 secret access key.
    @param bucket Bucket name.
    @param region AWS region (default ``us-east-1``; ignored by most S3-compatible services).
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._region = region
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict[str, Any]:
        """@brief Build kwargs for the S3 client context manager."""
        return {
            "service_name": "s3",
            "endpoint_url": self._endpoint_url,
            "aws_access_key_id": self._access_key,
            "aws_secret_access_key": self._secret_key,
            "region_name": self._region,
        }

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """@brief Upload an object to S3."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                await s3.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
            logger.debug("s3_put", key=key, size=len(data), bucket=self._bucket)
        except ClientError as exc:
            raise StorageError(f"S3 put failed for {key}: {exc}") from exc

    async def get(self, key: str) -> bytes:
        """@brief Download an object from S3."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                response = await s3.get_object(Bucket=self._bucket, Key=key)
                return cast(bytes, await response["Body"].read())
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                raise StorageKeyNotFoundError(key) from exc
            raise StorageError(f"S3 get failed for {key}: {exc}") from exc

    async def delete(self, key: str) -> None:
        """@brief Delete an object from S3. No-op if the key does not exist."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                await s3.delete_object(Bucket=self._bucket, Key=key)
            logger.debug("s3_delete", key=key, bucket=self._bucket)
        except ClientError as exc:
            raise StorageError(f"S3 delete failed for {key}: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """@brief Check whether an object exists in S3 via head_object."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise StorageError(f"S3 exists check failed for {key}: {exc}") from exc

    async def get_size(self, key: str) -> int:
        """@brief Return the size of an object in S3 via head_object."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                response = await s3.head_object(Bucket=self._bucket, Key=key)
                return int(response["ContentLength"])
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                raise StorageKeyNotFoundError(key) from exc
            raise StorageError(f"S3 get_size failed for {key}: {exc}") from exc

    async def check_health(self) -> bool:
        """@brief Verify the bucket is reachable via head_bucket."""
        try:
            async with self._session.client(**self._client_kwargs()) as s3:
                await s3.head_bucket(Bucket=self._bucket)
                return True
        except Exception:
            logger.warning("s3_health_check_failed", exc_info=True)
            return False
