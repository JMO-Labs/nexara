"""
@file interests.py
@brief Interest profile API routes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.i18n import _
from app.models.user import User
from app.repositories.interest_repo import InterestCategoryRepository, InterestRepository
from app.schemas.common import MessageResponse
from app.schemas.interest import (
    InterestAnalytics,
    InterestCategoryResponse,
    InterestCreate,
    InterestResponse,
    UserInterestsResponse,
)
from app.services.interest_service import InterestService

router = APIRouter(prefix="/interests", tags=["interests"])


def _get_interest_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InterestService:
    """@brief Build InterestService with injected dependencies."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    return InterestService(
        interest_repo=InterestRepository(db),
        category_repo=InterestCategoryRepository(db),
        community_id=community_id,
    )


@router.post("/", response_model=InterestResponse, status_code=status.HTTP_201_CREATED)
async def add_interest(
    body: InterestCreate,
    user: User = Depends(get_current_user),
    service: InterestService = Depends(_get_interest_service),
) -> InterestResponse:
    """@brief Add an interest for the authenticated user."""
    interest = await service.add_interest(
        user_id=user.id,
        category_slug=body.category_slug,
        value=body.value,
        source="manual",
    )
    return InterestResponse.model_validate(interest)


@router.delete("/{interest_id}", response_model=MessageResponse)
async def remove_interest(
    interest_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: InterestService = Depends(_get_interest_service),
) -> MessageResponse:
    """@brief Remove an interest for the authenticated user."""
    await service.remove_interest(interest_id, user.id)
    return MessageResponse(message=_("Interest removed"))


@router.get("/users/{user_id}/interests", response_model=UserInterestsResponse)
async def get_user_interests(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: InterestService = Depends(_get_interest_service),
) -> UserInterestsResponse:
    """@brief Get interests for a user (authenticated users only)."""
    return await service.list_user_interests(user_id)


@router.get("/categories", response_model=list[InterestCategoryResponse])
async def list_categories(
    service: InterestService = Depends(_get_interest_service),
) -> list[InterestCategoryResponse]:
    """@brief List all interest categories (public)."""
    return await service.list_categories()


@router.get("/admin/interests/analytics", response_model=list[InterestAnalytics])
async def get_interest_analytics(
    _admin: User = Depends(require_role("admin")),
    service: InterestService = Depends(_get_interest_service),
) -> list[InterestAnalytics]:
    """@brief Get aggregated interest analytics (admin only)."""
    return await service.get_analytics()
