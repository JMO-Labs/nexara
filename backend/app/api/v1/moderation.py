"""
@file moderation.py
@brief Moderation API: content reports, admin review, user blocking,
NSFW tagging.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.moderation import (
    BlockResponse,
    ReportAction,
    ReportActionResponse,
    ReportCreate,
    ReportCreated,
    ReportResponse,
)
from app.services.moderation_service import ModerationService
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus

router = APIRouter(tags=["moderation"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModerationService:
    """@brief Build ModerationService with injected dependencies."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        event_bus=event_bus,
    )
    return ModerationService(
        repo=ModerationRepository(db),
        audit_repo=AuditRepository(db),
        notification_service=notif,
        session=db,
        community_id=community_id,
    )


@router.post(
    "/moderation/reports",
    response_model=ReportCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    body: ReportCreate,
    user: User = Depends(get_current_user),
    service: ModerationService = Depends(_build_service),
) -> ReportCreated:
    """@brief Submit a content report."""
    report = await service.create_report(
        user.id, body.target_type, body.target_id, body.reason, body.description
    )
    return ReportCreated.model_validate(report)


@router.get("/admin/moderation/reports", response_model=PaginatedResponse[ReportResponse])
async def list_reports(
    status_filter: str | None = Query(
        None, alias="status", pattern="^(pending|reviewed|dismissed)$"
    ),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    _admin: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> PaginatedResponse[ReportResponse]:
    """@brief List reports (admin only), filterable by status."""
    items, next_cursor = await service.list_reports(status_filter, limit, cursor)
    return PaginatedResponse(
        items=[ReportResponse.model_validate(r) for r in items],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.post("/admin/moderation/reports/{report_id}/action", response_model=ReportActionResponse)
async def report_action(
    report_id: uuid.UUID,
    body: ReportAction,
    admin: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> ReportActionResponse:
    """@brief Apply an admin action to a report."""
    report = await service.take_action(report_id, admin.id, body.action, body.note)
    return ReportActionResponse.model_validate(report)


@router.get("/users/blocked", response_model=list[BlockResponse])
async def list_blocked(
    user: User = Depends(get_current_user),
    service: ModerationService = Depends(_build_service),
) -> list[BlockResponse]:
    """@brief List users blocked by the current user."""
    return [BlockResponse.model_validate(b) for b in await service.list_blocks(user.id)]


@router.post(
    "/users/{user_id}/block",
    response_model=BlockResponse,
    status_code=status.HTTP_201_CREATED,
)
async def block_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ModerationService = Depends(_build_service),
) -> BlockResponse:
    """@brief Block a user."""
    return BlockResponse.model_validate(await service.block_user(user.id, user_id))


@router.delete("/users/{user_id}/block", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ModerationService = Depends(_build_service),
) -> Response:
    """@brief Remove a block."""
    await service.unblock_user(user.id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/moderation/posts/{post_id}/mark-nsfw", response_model=MessageResponse)
async def mark_post_nsfw(
    post_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Flag a post as NSFW (admin only)."""
    await service.mark_nsfw("posts", post_id, user.id)
    return MessageResponse(message=_("Post marked NSFW"))


@router.post("/admin/moderation/media/{media_id}/mark-nsfw", response_model=MessageResponse)
async def mark_media_nsfw(
    media_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: ModerationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Flag a media item as NSFW (admin only)."""
    await service.mark_nsfw("media", media_id, user.id)
    return MessageResponse(message=_("Media marked NSFW"))
