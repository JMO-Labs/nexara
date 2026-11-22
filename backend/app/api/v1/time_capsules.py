"""
@file time_capsules.py
@brief Time capsule endpoints. No PATCH: a sealed capsule is immutable.
       Responses are unions so sealed capsules carry no ``body`` key.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.schemas.time_capsule import CapsuleCreate, CapsuleList, CapsuleOpen, CapsuleSealed
from app.services.notification_service import NotificationService
from app.services.time_capsule_service import TimeCapsuleService

router = APIRouter(prefix="/capsules", tags=["time-capsules"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TimeCapsuleService:
    """@brief Build TimeCapsuleService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return TimeCapsuleService(TimeCapsuleRepository(db), CommunityRepository(db), notif, cid)


@router.post("", status_code=201, response_model=CapsuleOpen)
async def create_capsule(
    body: CapsuleCreate,
    user: User = Depends(get_current_user),
    service: TimeCapsuleService = Depends(_build_service),
) -> Any:
    """@brief Seal a capsule."""
    return await service.create(user.id, body)


@router.get("", response_model=CapsuleList)
async def list_capsules(
    user: User = Depends(get_current_user),
    service: TimeCapsuleService = Depends(_build_service),
) -> Any:
    """@brief Sealed / opened / mine capsules for the viewer."""
    return await service.list_for_viewer(user.id)


@router.get("/{capsule_id}", response_model=CapsuleOpen | CapsuleSealed)
async def get_capsule(
    capsule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TimeCapsuleService = Depends(_build_service),
) -> Any:
    """@brief One capsule; sealed fields only until opened (author sees all)."""
    return await service.get(capsule_id, user.id)


@router.delete("/{capsule_id}", status_code=204)
async def delete_capsule(
    capsule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TimeCapsuleService = Depends(_build_service),
) -> Response:
    """@brief Delete own capsule."""
    await service.delete(capsule_id, user.id)
    return Response(status_code=204)
