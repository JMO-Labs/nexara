"""
@file reconnect.py
@brief Reconnect-nudge endpoint: snooze reminders about one person for 90 days.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.reconnect_repo import ReconnectRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService
from app.services.reconnect_service import ReconnectService

router = APIRouter(prefix="/reconnect", tags=["reconnect"])


class SnoozeBody(BaseModel):
    """@brief Optional JSON body; the notification action sends ``?target_id=`` instead."""

    target_id: uuid.UUID | None = None


class SnoozeOut(BaseModel):
    """@brief When the snooze ends."""

    until: datetime


def build_service(db: AsyncSession, cid: uuid.UUID) -> ReconnectService:
    """@brief ReconnectService wired to ``db``."""
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return ReconnectService(
        ReconnectRepository(db), UserRepository(db), CommunityRepository(db), notif, cid
    )


@router.post("/snooze", response_model=SnoozeOut)
async def snooze(
    body: SnoozeBody | None = None,
    target_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Snooze reminders about ``target_id`` (body or query) for 90 days."""
    tid = target_id or (body.target_id if body else None)
    if tid is None:
        raise AppError("VALIDATION_ERROR", "target_id is required", 422)
    svc = build_service(db, uuid.UUID(settings.COMMUNITY_ID))
    return SnoozeOut(until=await svc.snooze(user.id, tid, datetime.now(UTC)))
