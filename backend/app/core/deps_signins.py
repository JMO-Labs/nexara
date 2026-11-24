"""
@file deps_signins.py
@brief FastAPI dependency for the admin sign-in log service.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.db.session import async_session_factory
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.signin_repo import SigninRepository
from app.services.admin_signin_service import AdminSigninService


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
