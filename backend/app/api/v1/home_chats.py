"""
@file home_chats.py
@brief GET /api/v1/home/chats: ranked chat threads with unread state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.chat_read_repo import ChatReadRepository
from app.repositories.chat_repo import ChatChannelRepository
from app.schemas.home_chats import HomeChatsResponse
from app.services.home_chats_service import HomeChatsService

router = APIRouter(prefix="/chats", tags=["home_chats"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HomeChatsService:
    """@brief Build HomeChatsService with injected repos."""
    return HomeChatsService(ChatChannelRepository(db), ChatReadRepository(db), user.community_id)


@router.get("", response_model=HomeChatsResponse)
async def get_home_chats(
    user: User = Depends(get_current_user),
    service: HomeChatsService = Depends(_build_service),
    limit: int = Query(4, ge=1, le=20),
) -> HomeChatsResponse:
    """@brief Return the viewer's top chat threads."""
    return await service.list(user, limit)
