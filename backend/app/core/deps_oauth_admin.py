"""
@file deps_oauth_admin.py
@brief FastAPI dependency for the admin OAuth service (keeps repos out of routes).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.oauth.admin_oauth_service import AdminOAuthService


def get_admin_oauth_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminOAuthService:
    """@brief Provide an AdminOAuthService (admin only) with audit logging."""
    from app.services.oauth.admin_oauth_service import AdminOAuthService

    return AdminOAuthService(
        db, uuid.UUID(settings.COMMUNITY_ID), settings, user.id, client_ip(request)
    )
