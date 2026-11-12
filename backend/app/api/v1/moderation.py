"""
@file moderation.py
@brief Admin moderation endpoints (mark posts/media NSFW). Admin role required.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
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
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ModerationService:
    """@brief Build ModerationService with injected dependencies."""
    return ModerationService(
        ModerationRepository(db), AuditRepository(db), uuid.UUID(settings.COMMUNITY_ID)
    )


def _ip(request: Request) -> str | None:
    """@brief Client IP of the request."""
    return request.client.host if request.client else None


@router.post("/posts/{post_id}/mark-nsfw", response_model=MessageResponse)
async def mark_post_nsfw(
    post_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Mark a post NSFW."""
    await service.mark_nsfw("post", post_id, user, _ip(request))
    return MessageResponse(message=_("Post marked NSFW"))


@router.post("/media/{media_id}/mark-nsfw", response_model=MessageResponse)
async def mark_media_nsfw(
    media_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Mark a media item NSFW."""
    await service.mark_nsfw("media", media_id, user, _ip(request))
    return MessageResponse(message=_("Media marked NSFW"))
