"""
@file chat.py
@brief Chat REST endpoints — channel list, history, DMs.

Real-time message delivery runs over WebSocket; this router only
exposes the HTTP surface used by the frontend for initial page
rendering and pagination (channel list, history cursor, DM
create-or-fetch, DM thread list).
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.chat_repo import ChatChannelRepository, ChatMessageRepository
from app.repositories.moderation_repo import ModerationRepository
from app.schemas.chat import (
    ChannelResponse,
    DirectMessageThreadResponse,
    MessageHistoryResponse,
)
from app.services.chat_service import ChatService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the active community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> ChatService:
    """@brief Build a ChatService bound to the request-scoped session."""
    return ChatService(
        channel_repo=ChatChannelRepository(db),
        message_repo=ChatMessageRepository(db),
        community_id=community_id,
        moderation_repo=ModerationRepository(db),
    )


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
) -> list[ChannelResponse]:
    """@brief List every channel the authenticated user can access."""
    channels = await service.list_channels(user)
    return [ChannelResponse.model_validate(c) for c in channels]


@router.get(
    "/channels/{channel_id}/messages",
    response_model=MessageHistoryResponse,
)
async def get_history(
    channel_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> MessageHistoryResponse:
    """@brief Return a paginated page of message history (newest first)."""
    result = await service.get_history(
        user,
        channel_id,
        cursor=cursor,
        limit=limit,
    )
    return MessageHistoryResponse(
        items=result["items"],
        cursor=result["cursor"],
        has_more=result["has_more"],
    )


@router.post("/dm/{peer_id}", response_model=ChannelResponse, status_code=200)
async def create_or_get_dm(
    peer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
) -> ChannelResponse:
    """@brief Return (creating when absent) the DM channel with ``peer_id``."""
    channel = await service.create_or_get_dm(user, peer_id)
    return ChannelResponse.model_validate(channel)


@router.post(
    "/subgroup/{subgroup_id}",
    response_model=ChannelResponse,
    status_code=200,
)
async def ensure_subgroup_channel(
    subgroup_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
) -> ChannelResponse:
    """@brief Return (creating when absent) the subgroup chat channel."""
    channel = await service.ensure_subgroup_channel(user, subgroup_id)
    return ChannelResponse.model_validate(channel)


@router.delete("/dm/{channel_id}", status_code=204)
async def delete_dm_thread(
    channel_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
) -> None:
    """@brief Remove the calling user from a DM channel (hides it for them)."""
    await service.leave_dm(user, channel_id)


@router.get("/dm", response_model=list[DirectMessageThreadResponse])
async def list_dm_threads(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_build_service),
) -> list[DirectMessageThreadResponse]:
    """@brief List every DM thread the user participates in."""
    threads = await service.list_dm_threads(user)
    return [DirectMessageThreadResponse.model_validate(t) for t in threads]
