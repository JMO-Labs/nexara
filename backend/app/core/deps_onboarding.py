"""
@file deps_onboarding.py
@brief DI for OnboardingService (keeps repos out of routes).
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
    from app.models.user import User
    from app.services.onboarding_service import OnboardingService


def get_onboarding_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OnboardingService:
    """@brief OnboardingService for the current user (admin routes add a role guard)."""
    from app.repositories.audit_repo import AuditRepository
    from app.repositories.onboarding_repo import OnboardingRepository
    from app.repositories.two_factor_repo import TwoFactorRepository
    from app.services.onboarding_service import OnboardingService

    return OnboardingService(
        OnboardingRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        db,
        user,
        AuditRepository(db),
        client_ip(request),
        two_factor_repo=TwoFactorRepository(db),
    )
