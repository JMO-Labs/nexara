"""
@file users_directory.py
@brief GET /api/v1/users/directory: searchable people directory for members.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.people_directory_repo import PeopleDirectoryRepository
from app.schemas.people_directory import DirectoryResponse
from app.services.people_directory_service import PeopleDirectoryService

router = APIRouter(prefix="/users", tags=["users"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PeopleDirectoryService:
    """@brief Build PeopleDirectoryService with injected repo."""
    return PeopleDirectoryService(PeopleDirectoryRepository(db), user.community_id)


@router.get("/directory", response_model=DirectoryResponse)
async def get_directory(
    user: User = Depends(get_current_user),
    service: PeopleDirectoryService = Depends(_build_service),
    q: str | None = Query(None, max_length=100),
    filter: Literal["all", "online", "groups"] = Query("all"),
    limit: int = Query(24, ge=1, le=100),
    cursor: str | None = Query(None),
) -> DirectoryResponse:
    """@brief Return a page of community members visible to the viewer."""
    return await service.list(user, q=q, filter=filter, limit=limit, cursor=cursor)
