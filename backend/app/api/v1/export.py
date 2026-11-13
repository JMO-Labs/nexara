"""
@file export.py
@brief Data-export API: request an export and poll its status.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError
from app.core.i18n import _
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.user_export_repo import UserExportRepository
from app.schemas.export import ExportRequested, ExportStatus

router = APIRouter(prefix="/export", tags=["export"])

RATE_LIMIT_TTL_SECONDS = 86400


def _get_repo(db: AsyncSession = Depends(get_db)) -> UserExportRepository:
    """@brief Build the export repository."""
    return UserExportRepository(db)


def _get_redis() -> Redis:
    """@brief Valkey client used for the daily request counter."""
    return get_pool(get_settings(), DB_CACHE)


def _get_enqueue() -> Callable[[str, str], Any]:
    """@brief Return a callable that queues ``generate_user_export``."""

    def enqueue(user_id: str, export_id: str) -> Any:
        from app.tasks.export_tasks import generate_user_export

        return generate_user_export.apply_async((user_id, export_id), queue="default")

    return enqueue


@router.post("/request", response_model=ExportRequested)
async def request_export(
    user: User = Depends(get_current_user),
    repo: UserExportRepository = Depends(_get_repo),
    redis: Redis = Depends(_get_redis),
    enqueue: Callable[[str, str], Any] = Depends(_get_enqueue),
) -> Any:
    """@brief Create an export (1 per user per day) and enqueue generation."""
    key = f"export_request:{user.id}:{datetime.now(UTC).date().isoformat()}"
    if not await redis.set(key, "1", nx=True, ex=RATE_LIMIT_TTL_SECONDS):
        raise RateLimitError(_("You can request one export per day"))
    try:
        row = await repo.create(user.id, user.community_id)
        await repo.commit()
        enqueue(str(user.id), str(row.id))
    except Exception:
        await redis.delete(key)  # no export exists; don't lock the user out
        raise
    return ExportRequested(export_id=row.id, status=row.status, created_at=row.created_at)


@router.get("/{export_id}/status", response_model=ExportStatus)
async def export_status(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    repo: UserExportRepository = Depends(_get_repo),
) -> ExportStatus:
    """@brief Owner-only export status; download_url only when ready and unexpired."""
    row = await repo.get_by_id(export_id, user.community_id)
    if row is None:
        raise NotFoundError(_("Export not found"))
    if row.user_id != user.id:
        raise AuthorizationError()
    status = row.status
    url = None
    if status == "ready" and row.expires_at is not None:
        if datetime.now(UTC) > row.expires_at:
            status = "expired"
        else:
            url = f"/api/v1/export/{row.id}/download"
    return ExportStatus(
        export_id=row.id,
        status=status,
        created_at=row.created_at,
        ready_at=row.ready_at,
        expires_at=row.expires_at,
        file_size_bytes=row.file_size_bytes,
        download_url=url,
    )
