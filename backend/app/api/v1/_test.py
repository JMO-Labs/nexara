"""
@file _test.py
@brief Test-only endpoints (e2e helpers). Mounted only when
``settings.APP_ENV == "test"``; see ``app.main._register_routers``.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/_test", tags=["test-only"])


class NotifyRequest(BaseModel):
    """@brief Body for ``POST /_test/notify``."""

    type: str
    payload: dict[str, Any]


class NotifyResponse(BaseModel):
    """@brief Id of the created notification."""

    id: uuid.UUID


def get_notification_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationService:
    """@brief Build a NotificationService for the default community."""
    return NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=uuid.UUID(settings.COMMUNITY_ID),
        dispatcher=get_dispatcher(),
    )


@router.post("/notify", response_model=NotifyResponse, status_code=status.HTTP_201_CREATED)
async def notify(
    body: NotifyRequest,
    user: User = Depends(get_current_user),
    svc: NotificationService = Depends(get_notification_service),
) -> NotifyResponse:
    """
    @brief Send a notification of the given type to the current user.

    @param body Notification type key and payload.
    @return The created notification id.
    """
    n = await svc.notify(user.id, body.type, body.payload)
    return NotifyResponse(id=n.id)
