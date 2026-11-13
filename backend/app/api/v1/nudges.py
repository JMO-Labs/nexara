"""
@file nudges.py
@brief Nudge API endpoints: send a nudge to another user.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.nudge_repo import NudgeRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.schemas.nudge import NudgeResponse
from app.services.notification_service import NotificationService
from app.services.nudge_service import NudgeService

router = APIRouter(tags=["nudges"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NudgeService:
    """@brief Build NudgeService with injected dependencies."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db),
        SettingsRepository(db),
        community_id,
        dispatcher=get_dispatcher(),
    )
    return NudgeService(NudgeRepository(db), UserRepository(db), notif, community_id)


@router.post("/nudges/{user_id}", response_model=NudgeResponse, status_code=201)
async def send_nudge(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NudgeService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Nudge a user (400 self, 403 blocked, 429 within 24h)."""
    return await service.send(user, user_id)
