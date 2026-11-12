"""
@file export.py
@brief Personal data export API: request an export, check its status.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.user_export_repo import UserExportRepository
from app.schemas.export import ExportRequestResponse, ExportStatus
from app.services.export_service import ExportService
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/export", tags=["export"])

EXPORT_TASK = "app.tasks.export_tasks.generate_user_export"
"""@brief Celery task name that builds the export archive."""


def enqueue_export(export_id: uuid.UUID) -> None:
    """@brief Schedule export generation by task name. @param export_id Export id."""
    celery_app.send_task(EXPORT_TASK, args=[str(export_id)])


def _get_valkey(settings: Settings = Depends(get_settings)) -> Redis:
    """@brief Shared Valkey cache client."""
    return get_pool(settings, DB_CACHE)


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    valkey: Redis = Depends(_get_valkey),
) -> ExportService:
    """@brief Build ExportService with injected dependencies."""
    return ExportService(
        UserExportRepository(db), uuid.UUID(settings.COMMUNITY_ID), valkey, enqueue_export
    )


@router.post("/request", response_model=ExportRequestResponse, status_code=201)
async def request_export(
    user: User = Depends(get_current_user),
    service: ExportService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Request a personal data export (1 per user per day)."""
    return await service.request_export(user.id)


@router.get("/{export_id}/status", response_model=ExportStatus)
async def export_status(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ExportService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Get status of one of the current user's exports."""
    return await service.get_status(export_id, user.id)
