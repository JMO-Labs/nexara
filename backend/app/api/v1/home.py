"""
@file home.py
@brief Home aggregation endpoints: summary stats and media carousel feed.

Provides two routes under /home prefix for the home-page redesign:
  - GET /summary  — activity summary for the welcome banner
  - GET /media    — aggregated media for the carousel widget
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.event_repo import EventRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.home import HomeSummaryResponse
from app.schemas.subgroup import MediaAggregateListResponse, MediaItemResponse
from app.services.home_service import HomeService

router = APIRouter(prefix="/home", tags=["home"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> HomeService:
    """@brief Build HomeService with all dependencies injected."""
    return HomeService(
        post_repo=PostRepository(db),
        event_repo=EventRepository(db),
        notification_repo=NotificationRepository(db),
        subgroup_repo=SubgroupRepository(db),
        media_repo=SubgroupMediaRepository(db),
        community_id=community_id,
    )


@router.get("/summary", response_model=HomeSummaryResponse)
async def get_summary(
    user: User = Depends(get_current_user),
    service: HomeService = Depends(_build_service),
) -> HomeSummaryResponse:
    """
    @brief Return activity summary for the authenticated user's home banner.

    Counts new posts since last visit, upcoming events in next 7 days,
    and unread notification count.
    """
    return await service.summary(user=user)


@router.get("/media", response_model=MediaAggregateListResponse)
async def list_home_media(
    user: User = Depends(get_current_user),
    service: HomeService = Depends(_build_service),
    limit: int = Query(24, ge=1, le=200),
    cursor: str | None = Query(None),
    source: str = Query("all"),
) -> MediaAggregateListResponse:
    """
    @brief Return aggregated media across user's visible subgroups.

    Suitable for the home-page media carousel widget.
    """
    items, next_cursor = await service.list_media(
        user=user,
        limit=limit,
        cursor=cursor,
        source=source,
    )
    return MediaAggregateListResponse(
        items=[MediaItemResponse(**item) for item in items],
        next_cursor=next_cursor,
    )
