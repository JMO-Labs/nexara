"""
@file moderation.py
@brief Admin moderation endpoints: mark posts/media as NSFW.

POST /api/v1/admin/moderation/{posts|media}/{id}/mark-nsfw (admin only).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.moderation_repo import ModerationRepository
from app.schemas.common import MessageResponse
from app.services.moderation_service import ModerationService

router = APIRouter(prefix="/admin/moderation", tags=["moderation"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModerationService:
    """@brief Build ModerationService with injected dependencies."""
    return ModerationService(
        ModerationRepository(db), AuditRepository(db), uuid.UUID(settings.COMMUNITY_ID)
    )


@router.post("/posts/{post_id}/mark-nsfw", response_model=MessageResponse)
async def mark_post_nsfw(
    post_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Flag a post as NSFW (admin only)."""
    await service.mark_nsfw("posts", post_id, user.id)
    return MessageResponse(message=_("Post marked NSFW"))


@router.post("/media/{media_id}/mark-nsfw", response_model=MessageResponse)
async def mark_media_nsfw(
    media_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Flag a media item as NSFW (admin only)."""
    await service.mark_nsfw("media", media_id, user.id)
    return MessageResponse(message=_("Media marked NSFW"))
