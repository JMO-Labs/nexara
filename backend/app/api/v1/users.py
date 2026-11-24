"""
@file users.py
@brief User profile route handlers: get, update, list, password/email change, deactivation.

All routes require authentication.  The ``/me`` endpoints operate on the
current user; the ``/{user_id}`` endpoints return public profile data.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.deps_age import get_community
from app.core.i18n import _
from app.models.community import Community
from app.models.user import User
from app.repositories.profile_repo import ProfileRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.media import StorageUsageResponse
from app.schemas.profile import PluginUserResponse, ProfileResponse, UserSummaryResponse
from app.schemas.user import (
    EmailChangeRequest,
    PasswordChangeRequest,
    UserDetailResponse,
    UserUpdateRequest,
)
from app.services.age_service import age_group_source, effective_age_group
from app.services.profiles.service import ProfileService
from app.services.storage.usage_service import StorageUsageService
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserService:
    """@brief DI factory for UserService — overridable in tests."""
    return UserService(db, settings)


def _build_storage_service(db: AsyncSession = Depends(get_db)) -> StorageUsageService:
    """@brief DI factory for StorageUsageService — overridable in tests."""
    return StorageUsageService.from_session(db)


def _detail(user: User, community: Community | None) -> UserDetailResponse:
    """@brief Detail response with the effective (derived) age group."""
    out = UserDetailResponse.model_validate(user)
    out.age_group = effective_age_group(user, community)
    out.age_group_source = age_group_source(user, community)
    return out


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    community: Community | None = Depends(get_community),
) -> Any:
    """@brief Return the full profile of the authenticated user (age_group is effective)."""
    return _detail(user, community)


@router.patch("/me", response_model=UserDetailResponse)
async def update_profile(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community: Community | None = Depends(get_community),
) -> Any:
    """@brief Update profile fields for the authenticated user."""
    svc = UserService(db, settings)
    data = body.model_dump(exclude_unset=True)
    if "website_url" in data and data["website_url"] is not None:
        data["website_url"] = str(data["website_url"])
    return _detail(await svc.update_profile(user, data), community)


@router.post("/me/password", response_model=MessageResponse)
async def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Change the authenticated user's password."""
    svc = UserService(db, settings)
    await svc.change_password(user, body.current_password, body.new_password)
    return MessageResponse(message=_("Password updated successfully"))


@router.patch("/me/onboarding", response_model=UserDetailResponse)
async def complete_onboarding(
    user: User = Depends(get_current_user),
    svc: UserService = Depends(_build_service),
    community: Community | None = Depends(get_community),
) -> Any:
    """@brief Mark the onboarding tour as completed for the authenticated user."""
    return _detail(await svc.complete_onboarding(user), community)


@router.post("/me/email", response_model=UserDetailResponse)
async def change_email(
    body: EmailChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community: Community | None = Depends(get_community),
) -> Any:
    """@brief Change the authenticated user's email address."""
    svc = UserService(db, settings)
    return _detail(await svc.change_email(user, body.new_email, body.password), community)


@router.delete("/me", response_model=MessageResponse)
async def deactivate_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Soft-delete the authenticated user's account."""
    svc = UserService(db, settings)
    await svc.deactivate_account(user)
    return MessageResponse(message=_("Account deactivated"))


@router.get("/blocked", response_model=list[UserSummaryResponse])
async def list_blocked_users(
    user: User = Depends(get_current_user),
    svc: UserService = Depends(_build_service),
) -> Any:
    """@brief Return users the current user has blocked (UI reference only)."""
    return await svc.list_blocked(user)


@router.get("/{user_id}/storage", response_model=StorageUsageResponse)
async def get_user_storage(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: StorageUsageService = Depends(_build_storage_service),
) -> Any:
    """@brief Return storage usage; callers may only read their own."""
    return await svc.get_usage(user, user_id)


@router.get("/lookup", response_model=UserSummaryResponse)
async def lookup_user(
    username: str = Query(..., min_length=1, max_length=64),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """@brief Resolve an @username to a member (for mention links)."""
    return await ProfileService(ProfileRepository(db), user.community_id).lookup(username, user)


@router.get("/{user_id}", response_model=None, responses={200: {"model": ProfileResponse}})
async def get_user_profile(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """@brief A member's profile, with each field filtered by its privacy level."""
    profile = await ProfileService(ProfileRepository(db), user.community_id).view(user_id, user)
    if user.is_bot is True:  # plugins get public fields only, never members-only ones
        return PluginUserResponse.model_validate(profile, from_attributes=True)
    return profile


@router.get("", response_model=PaginatedResponse[UserSummaryResponse])
async def list_users(
    user: User = Depends(require_role("admin", "member")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> Any:
    """@brief List community members with cursor-based pagination."""
    svc = UserService(db, settings)
    users, next_cursor = await svc.list_users(
        user.community_id,
        limit=limit,
        cursor=cursor,
    )
    return PaginatedResponse(
        items=[UserSummaryResponse.model_validate(u) for u in users],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
