"""
@file home_people.py
@brief GET /api/v1/home/people: people strip for the home page.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.home_people_repo import HomePeopleRepository
from app.schemas.home_people import HomePeopleResponse
from app.services.home_people_service import HomePeopleService

router = APIRouter(prefix="/people", tags=["home_people"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HomePeopleService:
    """@brief Build HomePeopleService with injected repo."""
    return HomePeopleService(HomePeopleRepository(db), user.community_id)


@router.get("", response_model=HomePeopleResponse)
async def get_home_people(
    user: User = Depends(get_current_user),
    service: HomePeopleService = Depends(_build_service),
    limit: int = Query(10, ge=1, le=20),
) -> HomePeopleResponse:
    """@brief Return the viewer's people strip."""
    return await service.list(user, limit)
