"""
@file home_feed.py
@brief GET /api/v1/home/feed: unified posts + activity feed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.home_activity import _build_service as _build_activity_service
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.schemas.home_feed import HomeFeedResponse
from app.services.activity_service import ActivityService
from app.services.home_feed_service import HomeFeedService

router = APIRouter(prefix="/feed", tags=["home_feed"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    activity: ActivityService = Depends(_build_activity_service),
) -> HomeFeedService:
    """@brief Build HomeFeedService with injected repos."""
    return HomeFeedService(
        PostRepository(db), activity, SubgroupMemberRepository(db), user.community_id
    )


@router.get("", response_model=HomeFeedResponse)
async def get_home_feed(
    user: User = Depends(get_current_user),
    service: HomeFeedService = Depends(_build_service),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
) -> HomeFeedResponse:
    """@brief Return one page of the merged home feed for the viewer."""
    return await service.list(user, cursor, limit)
