"""
@file home_activity.py
@brief Home activity feed endpoint.

Provides GET /api/v1/home/activity for fetching aggregated community activity.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.activity import ActivityFeedResponse
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["home_activity"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityService:
    """@brief Build ActivityService with all dependencies injected."""
    return ActivityService(
        activity_repo=ActivityRepository(db),
        subgroup_repo=SubgroupRepository(db),
        post_repo=PostRepository(db),
        event_repo=EventRepository(db),
        gallery_repo=GalleryRepository(db),
        media_repo=SubgroupMediaRepository(db),
        community_id=user.community_id,
    )


@router.get("", response_model=ActivityFeedResponse)
async def get_activity_feed(
    user: User = Depends(get_current_user),
    service: ActivityService = Depends(_build_service),
    cursor: datetime | None = Query(None, description="ISO8601 cursor for pagination"),
    limit: int = Query(30, ge=1, le=100, description="Max items to return"),
) -> ActivityFeedResponse:
    """
    @brief Return activity feed for authenticated user.

    Aggregates community-wide activity events (posts, media, events, RSVPs, etc.)
    with read-time existence check and 60-minute aggregation window.

    Query params:
    - cursor: Optional ISO8601 datetime for cursor-based pagination.
    - limit: Max items (default 30, max 100).

    @param user Authenticated user.
    @param service ActivityService instance.
    @param cursor Optional pagination cursor.
    @param limit Max items to return.
    @return ActivityFeedResponse with paginated items and next_cursor.
    """
    return await service.list_for_user(user=user, cursor=cursor, limit=limit)
