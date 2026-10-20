"""
@file polls.py
@brief Polls API endpoints — vote, get poll, get results, close.

All endpoints require authentication.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.poll_repo import PollRepository
from app.schemas.common import MessageResponse
from app.schemas.poll import PollResponse, PollResultsResponse, VoteRequest
from app.services.poll_service import PollService
from app.services.realtime.event_bus import event_bus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/polls", tags=["polls"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> PollService:
    """@brief Build PollService with injected dependencies."""
    return PollService(
        poll_repo=PollRepository(db),
        community_id=community_id,
        event_bus=event_bus,
    )


@router.post("/{poll_id}/vote", response_model=PollResultsResponse)
async def cast_vote(
    poll_id: uuid.UUID,
    body: VoteRequest,
    user: User = Depends(get_current_user),
    service: PollService = Depends(_build_service),
) -> PollResultsResponse:
    """@brief Cast vote(s) on a poll."""
    return await service.cast_vote(poll_id, user.id, body.option_ids)


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PollService = Depends(_build_service),
) -> PollResponse:
    """@brief Get a poll with vote counts and user's vote (if applicable)."""
    return await service.get_poll(poll_id, user_id=user.id)


@router.get("/{poll_id}/results", response_model=PollResultsResponse)
async def get_poll_results(
    poll_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PollService = Depends(_build_service),
) -> PollResultsResponse:
    """@brief Get poll results (vote counts per option)."""
    return await service.get_results(poll_id)


@router.post("/{poll_id}/close", response_model=MessageResponse)
async def close_poll(
    poll_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PollService = Depends(_build_service),
) -> MessageResponse:
    """@brief Close a poll (creator only)."""
    await service.close_poll(poll_id, user.id)
    return MessageResponse(message=_("Poll closed"))
