"""
@file stories.py
@brief Voice story endpoints: ask / answer / decline requests, the question
       bank, and a member's Stories tab. Only the asker and teller see a request.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.story_repo import StoryRepository
from app.schemas.story import StoryAnswer, StoryAsk, StoryList, StoryRequestList, StoryRequestOut
from app.services.notification_service import NotificationService
from app.services.story_service import StoryService, question_bank

router = APIRouter(prefix="/stories", tags=["stories"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> StoryService:
    """@brief Build StoryService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return StoryService(StoryRepository(db), CommunityRepository(db), notif, cid)


@router.get("/questions", response_model=list[str])
async def suggested_questions(_user: User = Depends(get_current_user)) -> list[str]:
    """@brief The built-in bank of story-question suggestions."""
    return question_bank()


@router.post("/requests", status_code=201, response_model=StoryRequestOut)
async def ask_story(
    body: StoryAsk,
    user: User = Depends(get_current_user),
    service: StoryService = Depends(_build_service),
) -> Any:
    """@brief Ask a member to tell a story."""
    return await service.ask(user.id, body.teller_id, body.question)


@router.get("/requests", response_model=StoryRequestList)
async def list_requests(
    user: User = Depends(get_current_user), service: StoryService = Depends(_build_service)
) -> Any:
    """@brief Asks waiting for me (incoming) and asks I made (outgoing)."""
    return await service.list_for(user.id)


@router.get("/requests/{request_id}", response_model=StoryRequestOut)
async def get_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: StoryService = Depends(_build_service),
) -> Any:
    """@brief One request; 404 unless I am the asker or teller."""
    return await service.get(request_id, user.id)


@router.post("/requests/{request_id}/answer", response_model=StoryRequestOut)
async def answer_request(
    request_id: uuid.UUID,
    body: StoryAnswer,
    user: User = Depends(get_current_user),
    service: StoryService = Depends(_build_service),
) -> Any:
    """@brief Link my post (audio or text) as the answer."""
    return await service.answer(request_id, user.id, body.post_id)


@router.post("/requests/{request_id}/decline", status_code=204)
async def decline_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: StoryService = Depends(_build_service),
) -> Response:
    """@brief Silently decline; the asker is not told."""
    await service.decline(request_id, user.id)
    return Response(status_code=204)


@router.get("/users/{user_id}", response_model=StoryList)
async def user_stories(
    user_id: uuid.UUID,
    cursor: datetime | None = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    service: StoryService = Depends(_build_service),
) -> Any:
    """@brief A member's stories I may see, newest first."""
    return await service.stories_of(user_id, user.id, cursor, limit)
