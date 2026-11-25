"""
@file admin_system.py
@brief Admin: GET /admin/system health snapshot (cached 10 s).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.schemas.admin_system import SystemHealth
from app.services import system_health

router = APIRouter(
    prefix="/admin/system",
    tags=["admin-system"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=SystemHealth)
async def get_system_health(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> SystemHealth:
    """@brief Component health, disk and runtime info (admin only)."""
    return await system_health.collect_cached(db, settings)
