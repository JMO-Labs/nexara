"""
@file notifications.py
@brief Notification API endpoints — list, unread count, mark read.

All endpoints require authentication and operate on the current user's
notifications only.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.core.dependencies import get_webhook_service as _webhook_service
from app.core.i18n import _
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationList, UnreadCountResponse
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookListItem,
    WebhookUpdateRequest,
)
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus
from app.services.webhook_service import WebhookService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


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


@router.get("", response_model=NotificationList)
async def list_notifications(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> NotificationList:
    """@brief Return paginated list of notifications for the current user."""
    return await service.list_for_user(user.id, cursor=cursor, limit=limit)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> UnreadCountResponse:
    """@brief Return unread notification count for badge display."""
    return await service.get_unread_count(user.id)


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Mark a single notification as read."""
    ok = await service.mark_read(notification_id, user.id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=_("Notification not found"))
    return MessageResponse(message=_("Marked as read"))


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Mark all notifications as read for the current user."""
    count = await service.mark_all_read(user.id)
    return MessageResponse(message=_("Marked {count} as read").format(count=count))


@router.delete("", response_model=MessageResponse)
async def clear_all_notifications(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete all notifications for the current user."""
    count = await service.clear_all(user.id)
    return MessageResponse(message=_("Cleared {count} notifications").format(count=count))


@router.get("/webhooks", response_model=list[WebhookListItem])
async def list_webhooks(
    user: User = Depends(get_current_user),
    service: WebhookService = Depends(_webhook_service),
) -> list[WebhookListItem]:
    """@brief List the current user's webhook subscriptions (no secrets)."""
    return [WebhookListItem.model_validate(s) for s in await service.list_for_user(user.id)]


@router.post("/webhooks", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreateRequest,
    user: User = Depends(get_current_user),
    service: WebhookService = Depends(_webhook_service),
) -> WebhookCreateResponse:
    """@brief Create a user-level webhook; the secret is returned only here."""
    sub, secret = await service.create(user.id, body.url, body.type_keys)
    return WebhookCreateResponse(**WebhookListItem.model_validate(sub).model_dump(), secret=secret)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookListItem)
async def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdateRequest,
    user: User = Depends(get_current_user),
    service: WebhookService = Depends(_webhook_service),
) -> WebhookListItem:
    """@brief Partially update one of the user's webhooks."""
    sub = await service.update(
        user.id, webhook_id, url=body.url, type_keys=body.type_keys, enabled=body.enabled
    )
    return WebhookListItem.model_validate(sub)


@router.delete("/webhooks/{webhook_id}", response_model=MessageResponse)
async def delete_webhook(
    webhook_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: WebhookService = Depends(_webhook_service),
) -> MessageResponse:
    """@brief Delete one of the user's webhooks."""
    await service.delete(user.id, webhook_id)
    return MessageResponse(message=_("Webhook deleted"))
