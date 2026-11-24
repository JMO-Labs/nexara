"""
@file deps_signins.py
@brief FastAPI dependencies for the admin sign-in log and member session services.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.db.session import async_session_factory
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.signin_repo import SigninRepository
from app.repositories.token_repo import TokenRepository
from app.services.admin_signin_service import AdminSigninService
from app.services.session_service import SessionService


def get_admin_signin_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminSigninService:
    """@brief AdminSigninService (admin only) with audit logging and a streaming reader."""
    return AdminSigninService(
        SigninRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        AuditRepository(db),
        user.id,
        client_ip(request),
        db.commit,
        async_session_factory,
    )


def get_session_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionService:
    """@brief SessionService for the authenticated user; revocations are audited."""
    return SessionService(TokenRepository(db), user.id, AuditRepository(db), client_ip(request))
