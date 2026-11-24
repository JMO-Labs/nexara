"""
@file deps_two_factor.py
@brief FastAPI dependencies for the 2FA services (keeps repos out of routes).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.admin_security_service import AdminSecurityService
    from app.services.auth.two_factor import TwoFactorService


def _ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)


def get_two_factor_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TwoFactorService:
    """@brief Provide a TwoFactorService for the signed-in user."""
    from app.repositories.audit_repo import AuditRepository
    from app.repositories.two_factor_repo import TwoFactorRepository
    from app.repositories.user_repo import UserRepository
    from app.services.auth.two_factor import TwoFactorService

    return TwoFactorService(
        UserRepository(db),
        TwoFactorRepository(db),
        AuditRepository(db),
        settings,
        user,
        _ip(request),
    )


def get_admin_security_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminSecurityService:
    """@brief Provide an AdminSecurityService (admin only) with audit logging."""
    from app.repositories.audit_repo import AuditRepository
    from app.repositories.two_factor_repo import TwoFactorRepository
    from app.repositories.user_repo import UserRepository
    from app.services.admin_security_service import AdminSecurityService

    return AdminSecurityService(
        UserRepository(db),
        TwoFactorRepository(db),
        AuditRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        user.id,
        _ip(request),
    )
