"""
@file home_needs.py
@brief Home needs endpoint: GET /home/needs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.home_needs_repo import HomeNeedsRepository
from app.repositories.subgroup_member_repo import SubgroupMemberRepository
from app.schemas.home_needs import HomeNeedsResponse
from app.services.home_needs_service import HomeNeedsService

router = APIRouter(prefix="/needs", tags=["home_needs"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HomeNeedsService:
    """@brief Build HomeNeedsService with injected repos."""
    return HomeNeedsService(
        HomeNeedsRepository(db), SubgroupMemberRepository(db), user.community_id
    )


@router.get("", response_model=HomeNeedsResponse)
async def get_home_needs(
    user: User = Depends(get_current_user),
    service: HomeNeedsService = Depends(_build_service),
) -> HomeNeedsResponse:
    """@brief Return items that need the viewer's attention."""
    return await service.get(user)
