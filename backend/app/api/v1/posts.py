"""
@file posts.py
@brief Posts API endpoints — feed, CRUD, comments, and reactions.

Provides the core content endpoints for the activity feed.
All endpoints require authentication except where noted.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import CommentRepository, PostRepository, ReactionRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.post import CommentCreate, PostCreate, PostUpdate, ReactionResponse, ReactionToggle
from app.services.media_service import MediaService
from app.services.notification_service import NotificationService
from app.services.post_service import PostService
from app.services.realtime.pubsub import publish_to_community, publish_to_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/posts", tags=["posts"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_media_service(
    db: AsyncSession,
    community_id: uuid.UUID,
    settings: Settings,
) -> MediaService:
    """@brief Build MediaService for post media attachment."""
    from app.repositories.media_repo import MediaRepository
    from app.repositories.user_repo import UserRepository
    from app.services.storage.factory import get_storage_backend

    return MediaService(
        media_repo=MediaRepository(db),
        storage_backend=get_storage_backend(settings),
        user_repo=UserRepository(db),
        community_id=community_id,
    )


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> PostService:
    """@brief Build PostService with all dependencies injected."""
    notification_svc = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        pubsub_publisher=publish_to_user,
    )
    media_svc = _build_media_service(db, community_id, settings)

    return PostService(
        post_repo=PostRepository(db),
        comment_repo=CommentRepository(db),
        reaction_repo=ReactionRepository(db),
        notification_service=notification_svc,
        community_id=community_id,
        feed_publisher=publish_to_community,
        media_attacher=media_svc.attach_to_post,
    )


@router.get("")
async def list_feed(
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    """@brief Return paginated activity feed for the authenticated user."""
    return await service.list_feed(viewer_id=user.id, cursor=cursor, limit=limit)


@router.post("", status_code=201)
async def create_post(
    body: PostCreate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Create a new post with optional media attachments."""
    return await service.create_post(
        user=user,
        content=body.content,
        media_ids=body.media_ids,
    )


@router.get("/{post_id}")
async def get_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Return a single post with full enrichment."""
    return await service.get_post(post_id, viewer_id=user.id)


@router.put("/{post_id}")
async def update_post(
    post_id: uuid.UUID,
    body: PostUpdate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Edit post content (author only)."""
    return await service.update_post(post_id, user, body.content)


@router.delete("/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> MessageResponse:
    """@brief Soft-delete a post (author or admin only)."""
    await service.delete_post(post_id, user)
    return MessageResponse(message=_("Post deleted"))


@router.get("/{post_id}/comments")
async def list_comments(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
) -> dict[str, Any]:
    """@brief Return paginated comments for a post (newest first)."""
    return await service.list_comments(
        post_id,
        viewer_id=user.id,
        cursor=cursor,
        limit=limit,
    )


@router.post("/{post_id}/comments", status_code=201)
async def create_comment(
    post_id: uuid.UUID,
    body: CommentCreate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Add a comment to a post."""
    return await service.add_comment(
        post_id=post_id,
        user=user,
        content=body.content,
        parent_id=body.parent_id,
    )


@router.post("/{post_id}/reactions", response_model=ReactionResponse)
async def toggle_reaction(
    post_id: uuid.UUID,
    body: ReactionToggle,
    user: User = Depends(get_current_user),
    service: PostService = Depends(_build_service),
) -> ReactionResponse:
    """@brief Toggle a reaction on a post (add or remove)."""
    return await service.toggle_reaction(
        post_id=post_id,
        user=user,
        emoji=body.emoji,
    )
