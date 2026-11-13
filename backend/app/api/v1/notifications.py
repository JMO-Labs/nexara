"""
@file notifications.py
@brief Notification API: registry, list/bell, counts, read/dismiss,
delete and preferences. The SSE stream lives in ``sse.py``.

All endpoints require authentication and operate on the current user's
notifications only. Errors use the standard envelope.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.notification import (
    NotificationList,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService
from app.services.notifications import Category, to_json_schema
from app.services.notifications.dnd import resolve_snooze
from app.services.realtime.event_bus import event_bus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])

TYPES_CACHE_SECONDS = 3600
"""@brief Client cache lifetime for the type registry."""

BELL_LIMIT = 20
"""@brief Max rows returned by the bell (active) list."""


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> NotificationService:
    """@brief Build the NotificationService with injected dependencies."""
    return NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        event_bus=event_bus,
        dispatcher=get_dispatcher(),
    )


@router.get("/types")
async def list_types(
    request: Request,
    user: User = Depends(get_current_user),
) -> Response:
    """@brief Registry JSON with a strong ETag; 304 when If-None-Match matches."""
    data = json.dumps(to_json_schema(), sort_keys=True, separators=(",", ":"))
    etag = f'"{hashlib.sha256(data.encode()).hexdigest()[:32]}"'
    headers = {"ETag": etag, "Cache-Control": f"private, max-age={TYPES_CACHE_SECONDS}"}
    if etag in request.headers.get("if-none-match", ""):
        return Response(status_code=304, headers=headers)
    return Response(content=data, media_type="application/json", headers=headers)


@router.get("", response_model=NotificationList)
async def list_notifications(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    type: str | None = Query(None),  # noqa: A002
    category: Category | None = Query(None),
    unread_only: bool = Query(False),
) -> NotificationList:
    """@brief Paginated drawer list with optional type/category/unread filters."""
    return await service.list_for_user(
        user.id,
        cursor=cursor,
        limit=limit,
        type=type,
        category=category,
        unread_only=unread_only,
    )


@router.get("/active", response_model=list[NotificationResponse])
async def list_active(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> list[NotificationResponse]:
    """@brief Bell list: non-dismissed notifications, newest first (top 20)."""
    rows = await service.list_active(user.id, limit=BELL_LIMIT)
    return [NotificationResponse.model_validate(r) for r in rows]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> UnreadCountResponse:
    """@brief Unread total plus per-category breakdown for badges."""
    return await service.get_unread_count(user.id)


@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> NotificationPreferences:
    """@brief Per-type channel prefs plus DnD and digest settings."""
    return await service.get_preferences(user.id)


@router.patch("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    patch: NotificationPreferencesUpdate = Body(...),
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> NotificationPreferences:
    """@brief Partial update; 400 NOTIF_TYPE_UNKNOWN / NOTIF_PREF_INVALID."""
    return await service.update_preferences(user.id, patch)


class SnoozeRequest(BaseModel):
    """@brief Body for POST /snooze: ``1h``, ``until_morning`` or ISO-8601."""

    duration: str


@router.post("/snooze", response_model=MessageResponse)
async def snooze(
    body: SnoozeRequest,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Snooze email/push/toast; 400 NOTIF_PREF_INVALID on bad duration."""
    prefs = await service.get_preferences(user.id)
    until = resolve_snooze(body.duration, prefs.dnd_timezone, datetime.now(UTC))
    await service.snooze(user.id, until)
    return MessageResponse(message=_("Notifications snoozed"))


@router.delete("/snooze", response_model=MessageResponse)
async def clear_snooze(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief End the active snooze."""
    await service.clear_snooze(user.id)
    return MessageResponse(message=_("Snooze cleared"))


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
    type: str | None = Query(None),  # noqa: A002
    category: Category | None = Query(None),
) -> MessageResponse:
    """@brief Mark notifications read, optionally filtered by type/category."""
    count = await service.mark_all_read(user.id, type=type, category=category)
    return MessageResponse(message=_("Marked {count} as read").format(count=count))


@router.post("/dismiss-all", response_model=MessageResponse)
async def dismiss_all(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Clear the bell (dismiss every active notification)."""
    count = await service.dismiss_all(user.id)
    return MessageResponse(message=_("Dismissed {count} notifications").format(count=count))


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Mark a single notification as read; 404 if missing or not owned."""
    if not await service.mark_read(notification_id, user.id):
        raise NotFoundError(_("Notification not found"))
    return MessageResponse(message=_("Marked as read"))


@router.post("/{notification_id}/dismiss", response_model=MessageResponse)
async def dismiss_notification(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Dismiss one notification from the bell; 404 if missing or not owned."""
    await service.dismiss(user.id, notification_id)
    return MessageResponse(message=_("Dismissed"))


@router.delete("", response_model=MessageResponse)
async def clear_notifications(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
    type: str | None = Query(None),  # noqa: A002
    before: datetime | None = Query(None),
) -> MessageResponse:
    """@brief Bulk delete, optionally by type and/or created before a timestamp."""
    count = await service.clear_all(user.id, type=type, before=before)
    return MessageResponse(message=_("Cleared {count} notifications").format(count=count))


@router.delete("/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete one notification; 404 if missing or not owned."""
    await service.delete(user.id, notification_id)
    return MessageResponse(message=_("Deleted"))
