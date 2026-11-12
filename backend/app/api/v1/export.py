"""
@file export.py
@brief Data export API: request an export and poll its status.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.user_export_repo import UserExportRepository
from app.schemas.export import ExportRequested, ExportStatus
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> UserExportRepository:
    """@brief Build the export repository."""
    return UserExportRepository(db)


def _get_redis(settings: Settings = Depends(get_settings)) -> Any:
    """@brief Shared cache-DB Valkey client used for the daily rate limit."""
    return get_pool(settings, DB_CACHE)


def _get_enqueue() -> Callable[[str], None]:
    """@brief Return a callable that enqueues ``generate_user_export``."""

    def enqueue(export_id: str) -> None:
        from app.tasks.celery_app import celery_app

        celery_app.send_task("app.tasks.export_tasks.generate_user_export", args=[export_id])

    return enqueue


def _build_service(
    repo: UserExportRepository = Depends(_get_repo),
    redis: Any = Depends(_get_redis),
    enqueue: Callable[[str], None] = Depends(_get_enqueue),
    settings: Settings = Depends(get_settings),
) -> ExportService:
    """@brief Build ExportService with injected dependencies."""
    return ExportService(repo, redis, enqueue, uuid.UUID(settings.COMMUNITY_ID))


@router.post("/request", response_model=ExportRequested, status_code=202)
async def request_export(
    user: User = Depends(get_current_user),
    service: ExportService = Depends(_build_service),
) -> Any:
    """@brief Request a data export (one per user per day)."""
    return _requested(await service.request_export(user.id))


@router.get("/{export_id}/status", response_model=ExportStatus)
async def export_status(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExportService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Get the status of one of the caller's exports."""
    return await service.get_status(user.id, export_id)


def _requested(export: Any) -> dict[str, Any]:
    """@brief Shape a new export for the response."""
    return {"export_id": export.id, "status": export.status, "created_at": export.created_at}
