"""
@file admin_sso.py
@brief Admin endpoint to toggle SSO-only login enforcement.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_oauth import _client_ip, _community_id
from app.core.dependencies import get_db, require_role
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.services.auth import sso_only

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


class SsoOnlyUpdate(BaseModel):
    """@brief Request body for the SSO-only toggle."""

    enabled: bool


class SsoOnlyResponse(BaseModel):
    """@brief Current SSO-only state, with a lockout warning when enabled."""

    sso_only: bool
    warning: str | None = None


@router.patch("/sso-only", response_model=SsoOnlyResponse)
async def set_sso_only(
    body: SsoOnlyUpdate,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> SsoOnlyResponse:
    """@brief Enable/disable SSO-only mode (requires an enabled OIDC provider to enable)."""
    await sso_only.set_sso_only(db, community_id, body.enabled, user.id)
    await AuditRepository(db).append(
        actor_id=user.id,
        action="settings.sso_only.updated",
        target_type="community",
        target_id=community_id,
        extra_data={"enabled": body.enabled},
        ip_address=_client_ip(request),
    )
    return SsoOnlyResponse(
        sso_only=body.enabled,
        warning=sso_only.SSO_ONLY_WARNING if body.enabled else None,
    )
