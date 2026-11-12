"""
@file export_service.py
@brief Business logic for requesting and checking data exports.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError
from app.models.user_export import UserExport
from app.repositories.user_export_repo import UserExportRepository

RATE_LIMIT_TTL_SECONDS = 24 * 60 * 60


class ExportService:
    """@brief Rate-limited export requests and ownership-checked status reads."""

    def __init__(
        self,
        repo: UserExportRepository,
        redis: Any,
        enqueue: Callable[[str], None],
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._redis = redis
        self._enqueue = enqueue
        self._community_id = community_id

    async def request_export(self, user_id: uuid.UUID) -> UserExport:
        """
        @brief Create a pending export and enqueue generation.
        @param user_id Requesting user.
        @raises RateLimitError If the user already requested one today.
        """
        key = f"export_request:{user_id}:{datetime.now(UTC):%Y-%m-%d}"
        if not await self._redis.set(key, 1, ex=RATE_LIMIT_TTL_SECONDS, nx=True):
            raise RateLimitError("You can request one export per day")
        export = await self._repo.create_export(user_id, self._community_id)
        self._enqueue(str(export.id))
        return export

    async def get_status(self, user_id: uuid.UUID, export_id: uuid.UUID) -> dict[str, Any]:
        """
        @brief Return export status; ``expired`` and no URL once past expiry.
        @raises NotFoundError Unknown export. @raises AuthorizationError Not the owner.
        """
        export = await self._repo.get_by_id(export_id, self._community_id)
        if export is None:
            raise NotFoundError("Export not found")
        if export.user_id != user_id:
            raise AuthorizationError("Not your export")
        status = export.status
        url: str | None = None
        if status == "ready" and export.expires_at is not None:
            if datetime.now(UTC) > export.expires_at:
                status = "expired"
            else:
                url = f"/api/v1/export/{export.id}/download"
        return {
            "export_id": export.id,
            "status": status,
            "created_at": export.created_at,
            "ready_at": export.ready_at,
            "expires_at": export.expires_at,
            "file_size_bytes": export.file_size_bytes,
            "download_url": url,
        }
