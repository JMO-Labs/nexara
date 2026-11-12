"""
@file export_service.py
@brief Business logic for personal data export requests: daily rate limit,
       creation, task enqueueing and status reporting.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError
from app.repositories.user_export_repo import UserExportRepository

RATE_LIMIT_TTL_SECONDS = 24 * 60 * 60
"""@brief Lifetime of the per-user daily rate-limit key."""


class ExportService:
    """
    @brief Coordinates export requests and status lookups.
    @param repo UserExport repository.
    @param community_id Active community.
    @param valkey Counter store for the daily rate limit.
    @param enqueue Callable that schedules generation for an export id.
    """

    def __init__(
        self,
        repo: UserExportRepository,
        community_id: uuid.UUID,
        valkey: Redis,
        enqueue: Callable[[uuid.UUID], None],
    ) -> None:
        self._repo = repo
        self._community_id = community_id
        self._valkey = valkey
        self._enqueue = enqueue

    async def request_export(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        @brief Create a pending export if the user is under the daily limit.
        @param user_id Requesting user.
        @return Dict with export_id, status, created_at.
        """
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"export_request:{user_id}:{day}"
        count = int(await self._valkey.incr(key))
        if count == 1:
            await self._valkey.expire(key, RATE_LIMIT_TTL_SECONDS)
        if count > 1:
            raise RateLimitError("You can request one export per day")
        export = await self._repo.create(user_id, self._community_id)
        self._enqueue(export.id)
        return {"export_id": export.id, "status": export.status, "created_at": export.created_at}

    async def get_status(self, export_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        """
        @brief Return status for an export owned by the user.
        @param export_id Export id.
        @param user_id Requesting user (must own the export).
        @return ExportStatus-shaped dict; status 'expired' once past expires_at.
        """
        export = await self._repo.get_by_id(export_id, self._community_id)
        if export is None:
            raise NotFoundError("Export not found")
        if export.user_id != user_id:
            raise AuthorizationError("You do not have access to this export")
        status = export.status
        expired = export.expires_at is not None and datetime.now(UTC) > export.expires_at
        if expired:
            status = "expired"
        download_url = f"/api/v1/export/{export.id}/download" if status == "ready" else None
        return {
            "export_id": export.id,
            "status": status,
            "created_at": export.created_at,
            "ready_at": export.ready_at,
            "expires_at": export.expires_at,
            "file_size_bytes": export.file_size_bytes,
            "download_url": download_url,
        }
