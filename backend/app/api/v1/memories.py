"""
@file memories.py
@brief "On this day" memories route.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.user_repo import UserRepository
from app.schemas.post import PostResponse
from app.services.memories_service import MemoriesService

router = APIRouter(prefix="/memories", tags=["memories"])


def _service(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MemoriesService:
    """@brief MemoriesService bound to the request session."""
    return MemoriesService(
        PostMemoriesRepository(db), UserRepository(db), CommunityRepository(db), user.community_id
    )


@router.get("/on-this-day")
async def on_this_day(
    user: User = Depends(get_current_user), svc: MemoriesService = Depends(_service)
) -> dict[str, Any]:
    """@brief Posts from this local month/day in past years that you can open now."""
    out = await svc.on_this_day(user.id)
    return {
        "items": [PostResponse.model_validate(i).model_dump(mode="json") for i in out["items"]],
        "years_ago": out["years_ago"],
    }
