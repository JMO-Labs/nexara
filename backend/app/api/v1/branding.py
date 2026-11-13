"""
@file branding.py
@brief Branding API endpoints — public read, admin write.

GET /api/v1/branding/ is public (no auth required) so the landing page
and PWA manifest can consume branding data.  PUT requires admin role.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.branding_repo import BrandingRepository
from app.schemas.branding import (
    BrandingResponse,
    BrandingUpdate,
    BrandingUpdateResponse,
    PresetThemeList,
)
from app.services.branding_service import BrandingService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/branding", tags=["branding"])


def _get_cache_client(
    settings: Settings = Depends(get_settings),
) -> Redis | None:
    """@brief Provide the Valkey cache client, or None if unavailable."""
    try:
        return get_pool(settings, DB_CACHE)
    except Exception:
        return None


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


@router.get("/", response_model=BrandingResponse)
async def get_branding(
    db: AsyncSession = Depends(get_db),
    cache_client: Redis | None = Depends(_get_cache_client),
    community_id: uuid.UUID = Depends(_community_id),
) -> BrandingResponse:
    """
    @brief Return the current community branding (public, no auth required).

    Cached in Valkey for 5 minutes.  Returns default branding values if
    no branding row exists yet.
    """
    repo = BrandingRepository(db)
    service = BrandingService(repo=repo, cache_client=cache_client, community_id=community_id)
    return await service.get_branding()


@router.get("/manifest.json")
async def get_pwa_manifest(
    db: AsyncSession = Depends(get_db),
    cache_client: Redis | None = Depends(_get_cache_client),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    @brief Return PWA manifest (public, no auth required).

    Used by browsers when installing the app as a PWA.
    """
    repo = BrandingRepository(db)
    service = BrandingService(repo=repo, cache_client=cache_client, community_id=community_id)
    branding = await service.get_branding()
    return service.generate_pwa_manifest(branding, base_url=settings.APP_BASE_URL)


@router.get("/presets", response_model=PresetThemeList)
async def list_presets(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> PresetThemeList:
    """@brief Return the preset colour themes (public)."""
    service = BrandingService(repo=BrandingRepository(db), community_id=community_id)
    return PresetThemeList(themes=await service.get_preset_themes())


@router.post("/presets/{theme_name}/apply", response_model=BrandingUpdateResponse)
async def apply_preset(
    theme_name: str,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    cache_client: Redis | None = Depends(_get_cache_client),
    community_id: uuid.UUID = Depends(_community_id),
) -> BrandingUpdateResponse:
    """@brief Apply a preset theme's colours to the branding (admin only)."""
    service = BrandingService(
        repo=BrandingRepository(db),
        cache_client=cache_client,
        community_id=community_id,
        audit_repo=AuditRepository(db),
    )
    return await service.apply_preset_theme(
        theme_name,
        user_id=admin.id,
        ip_address=request.client.host if request.client else None,
    )


@router.put("/", response_model=BrandingUpdateResponse)
async def update_branding(
    data: BrandingUpdate,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    cache_client: Redis | None = Depends(_get_cache_client),
    community_id: uuid.UUID = Depends(_community_id),
) -> BrandingUpdateResponse:
    """
    @brief Update community branding fields (admin only).

    Invalidates the Valkey cache and writes an audit log entry.
    """
    repo = BrandingRepository(db)
    audit_repo = AuditRepository(db)
    service = BrandingService(
        repo=repo,
        cache_client=cache_client,
        community_id=community_id,
        audit_repo=audit_repo,
    )
    return await service.update_branding(
        user_id=admin.id,
        data=data,
        ip_address=request.client.host if request.client else None,
    )
