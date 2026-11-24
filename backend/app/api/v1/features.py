"""
@file features.py
@brief Feature flag routes: members read, admins change.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import RootModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.features import FEATURE_DEFAULTS
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.services.features_service import FeaturesService

router = APIRouter(tags=["features"])


class FeaturePatch(RootModel[dict[str, bool]]):
    """@brief Partial ``{key: bool}``; unknown keys fail validation (422)."""

    @model_validator(mode="after")
    def _known(self) -> FeaturePatch:
        unknown = set(self.root) - set(FEATURE_DEFAULTS)
        if unknown:
            raise ValueError(f"Unknown feature(s): {sorted(unknown)}")
        return self


def get_features_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FeaturesService:
    """@brief DI factory with audit logging bound to the caller."""
    ip = client_ip(request)
    return FeaturesService(
        CommunityRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        audit_repo=AuditRepository(db),
        actor_id=user.id,
        ip_address=ip,
    )


@router.get("/features")
async def get_features(
    svc: FeaturesService = Depends(get_features_service),
) -> dict[str, bool]:
    """@brief Effective flags for any member."""
    return await svc.get()


@router.get("/admin/features", dependencies=[Depends(require_role("admin"))])
async def admin_get_features(
    svc: FeaturesService = Depends(get_features_service),
) -> dict[str, bool]:
    """@brief Effective flags (admin)."""
    return await svc.get()


@router.put("/admin/features", dependencies=[Depends(require_role("admin"))])
async def admin_put_features(
    body: FeaturePatch,
    svc: FeaturesService = Depends(get_features_service),
) -> dict[str, bool]:
    """@brief Partial update; audit-logged."""
    return await svc.update(body.root)
