"""
@file deps_apprise.py
@brief FastAPI dependency for the admin Apprise service (keeps repos out of routes).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.admin_apprise_service import AdminAppriseService


def get_admin_apprise_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminAppriseService:
    """@brief Provide an AdminAppriseService (admin only) with audit logging."""
    from app.repositories.apprise_repo import AppriseRepository
    from app.repositories.audit_repo import AuditRepository
    from app.services.admin_apprise_service import AdminAppriseService

    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    return AdminAppriseService(
        AppriseRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        AuditRepository(db),
        user.id,
        ip,
    )
