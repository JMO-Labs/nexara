"""
@file deps_age.py
@brief DI for AgeService and the community row (keeps repos out of routes).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db

if TYPE_CHECKING:
    from app.models.community import Community
    from app.models.user import User
    from app.services.age_service import AgeService


async def get_community(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> Community | None:
    """@brief The current community row (None if missing)."""
    from app.repositories.age_repo import AgeRepository

    return await AgeRepository(db).get_community(uuid.UUID(settings.COMMUNITY_ID))


def get_age_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AgeService:
    """@brief AgeService for the current user (admin routes add a role guard)."""
    from app.core.list_dependencies import _notifier
    from app.repositories.age_repo import AgeRepository
    from app.repositories.audit_repo import AuditRepository
    from app.services.age_service import AgeService

    cid = uuid.UUID(settings.COMMUNITY_ID)
    return AgeService(
        AgeRepository(db), cid, user.id, AuditRepository(db), _notifier(db, cid), client_ip(request)
    )
