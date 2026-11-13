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
from app.core.i18n import _
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import (
    EmailChangeRequest,
    PasswordChangeRequest,
    UserDetailResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserService:
    """@brief DI factory for UserService — overridable in tests."""
    return UserService(db, settings)


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> Any:
    """@brief Return the full profile of the authenticated user."""
    return user


@router.patch("/me", response_model=UserDetailResponse)
async def update_profile(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Update profile fields for the authenticated user."""
    svc = UserService(db, settings)
    data = body.model_dump(exclude_unset=True)
    if "website_url" in data and data["website_url"] is not None:
        data["website_url"] = str(data["website_url"])
    return await svc.update_profile(user, data)


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
) -> Any:
    """@brief Mark the onboarding tour as completed for the authenticated user."""
    return await svc.complete_onboarding(user)


@router.post("/me/email", response_model=UserDetailResponse)
async def change_email(
    body: EmailChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Change the authenticated user's email address."""
    svc = UserService(db, settings)
    return await svc.change_email(user, body.new_email, body.password)


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


@router.get("/blocked", response_model=list[UserResponse])
async def list_blocked_users(
    user: User = Depends(get_current_user),
    svc: UserService = Depends(_build_service),
) -> Any:
    """@brief Return users the current user has blocked (UI reference only)."""
    return await svc.list_blocked(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Return the public profile of a user by ID."""
    svc = UserService(db, settings)
    return await svc.get_user(user_id)


@router.get("", response_model=PaginatedResponse[UserResponse])
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
        items=[UserResponse.model_validate(u) for u in users],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
