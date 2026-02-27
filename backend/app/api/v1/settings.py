"""
@file settings.py
@brief User settings API endpoints — per-user, authenticated.

All endpoints require authentication and operate on the current user's
settings only.  No user can access another user's settings.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel, EmailStr

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    NotificationPreferences,
    ProfileUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.settings_service import SettingsService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> SettingsService:
    """@brief Build the SettingsService with injected dependencies."""
    return SettingsService(
        settings_repo=SettingsRepository(db),
        user_repo=UserRepository(db),
        community_id=community_id,
    )


@router.get("/", response_model=UserSettingsResponse)
async def get_settings_endpoint(
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> UserSettingsResponse:
    """@brief Return the current user's settings."""
    return await service.get_settings(user.id)


@router.put("/", response_model=UserSettingsResponse)
async def update_settings_endpoint(
    data: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> UserSettingsResponse:
    """@brief Update general settings (theme, locale)."""
    return await service.update_settings(user.id, data)


@router.put("/profile", response_model=MessageResponse)
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> MessageResponse:
    """@brief Update profile fields (display_name, bio, location, etc.)."""
    await service.update_profile(user.id, data)
    return MessageResponse(message=_("Profile updated"))


class EmailChangeRequest(BaseModel):
    """@brief Payload for initiating an email change."""

    new_email: EmailStr


@router.put("/email", response_model=MessageResponse)
async def update_email(
    data: EmailChangeRequest,
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> MessageResponse:
    """@brief Initiate an email change (sends verification email)."""
    await service.update_email(user.id, data.new_email)
    return MessageResponse(message=_("Verification email sent"))


@router.get("/notifications", response_model=NotificationPreferences)
async def get_notification_preferences(
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> NotificationPreferences:
    """@brief Return notification preference toggles for the current user."""
    return await service.get_notification_preferences(user.id)


@router.put("/notifications", response_model=UserSettingsResponse)
async def update_notification_preferences(
    data: NotificationPreferences,
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(_build_service),
) -> UserSettingsResponse:
    """@brief Update notification preference toggles."""
    return await service.update_notification_preferences(user.id, data)
