"""
@file admin_retention.py
@brief Admin retention policy endpoints (admin role required).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_role
from app.models.user import User
from app.repositories.retention_repo import RetentionRepository
from app.schemas.admin_retention import RetentionPolicyOut, RetentionUpdate
from app.services.retention_service import RetentionService

router = APIRouter(prefix="/admin/retention", tags=["admin-retention"])


def _build_service(db: AsyncSession = Depends(get_db)) -> RetentionService:
    """@brief Build RetentionService with injected dependencies."""
    return RetentionService(RetentionRepository(db))


@router.get("", response_model=list[RetentionPolicyOut])
async def list_retention(
    _user: User = Depends(require_role("admin")),
    service: RetentionService = Depends(_build_service),
) -> list[RetentionPolicyOut]:
    """@brief All retention policies (defaults for keys never saved)."""
    return await service.list_policies()


@router.put("/{key}", response_model=RetentionPolicyOut)
async def update_retention(
    key: str,
    body: RetentionUpdate,
    user: User = Depends(require_role("admin")),
    service: RetentionService = Depends(_build_service),
) -> RetentionPolicyOut:
    """@brief Update one policy; unknown key returns 404."""
    return await service.update(key, body, user.id)
