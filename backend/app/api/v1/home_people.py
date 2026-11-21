"""
@file home_people.py
@brief GET /api/v1/home/people: people strip for the home page.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.home_people_repo import HomePeopleRepository
from app.schemas.home_people import FavoritesResponse, HomePeopleResponse
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


@router.put("/favorites/{user_id}", response_model=FavoritesResponse)
async def pin_person(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: HomePeopleService = Depends(_build_service),
) -> FavoritesResponse:
    """@brief Pin a person to the viewer's people strip."""
    return FavoritesResponse(favorites=await service.set_favorite(user, user_id, True))


@router.delete("/favorites/{user_id}", response_model=FavoritesResponse)
async def unpin_person(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: HomePeopleService = Depends(_build_service),
) -> FavoritesResponse:
    """@brief Unpin a person from the viewer's people strip."""
    return FavoritesResponse(favorites=await service.set_favorite(user, user_id, False))
