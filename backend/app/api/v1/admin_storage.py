"""
@file admin_storage.py
@brief Admin storage analytics endpoints (admin role required).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.models.user import User
from app.repositories.storage_repo import StorageRepository
from app.schemas.admin_storage import StorageResponse, UserStoragePage
from app.services.admin_storage_service import AdminStorageService

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminStorageService:
    """@brief Build AdminStorageService with injected dependencies."""
    return AdminStorageService(StorageRepository(db), uuid.UUID(settings.COMMUNITY_ID))


@router.get("", response_model=StorageResponse)
async def get_storage(
    days: int = Query(30, ge=1, le=365),
    _user: User = Depends(require_role("admin")),
    service: AdminStorageService = Depends(_build_service),
) -> StorageResponse:
    """@brief Current usage, snapshot trend and top users."""
    return await service.get_overview(days=days)


@router.get("/users", response_model=UserStoragePage)
async def list_storage_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    _user: User = Depends(require_role("admin")),
    service: AdminStorageService = Depends(_build_service),
) -> UserStoragePage:
    """@brief Paginated per-user storage breakdown."""
    return await service.list_users(page=page, page_size=page_size)
