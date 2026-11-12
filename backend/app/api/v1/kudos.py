"""
@file kudos.py
@brief Kudos API endpoints — create, list, list received, delete.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.kudos_repo import KudosRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.repositories.user_repo import UserRepository
from app.schemas.kudos import KudosCreate, KudosList, KudosResponse
from app.services.kudos_service import KudosService
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus

router = APIRouter(prefix="/kudos", tags=["kudos"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> KudosService:
    """@brief Build KudosService with injected dependencies."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), community_id, event_bus=event_bus
    )
    return KudosService(
        KudosRepository(db), UserRepository(db), SubgroupRepository(db), notif, community_id
    )


@router.post("", status_code=201, response_model=KudosResponse)
async def create_kudos(
    body: KudosCreate,
    user: User = Depends(get_current_user),
    service: KudosService = Depends(_build_service),
) -> KudosResponse:
    """@brief Give kudos to a user."""
    return await service.create(user, body)


@router.get("", response_model=KudosList)
async def list_kudos(
    user: User = Depends(get_current_user),
    service: KudosService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    """@brief Recent kudos."""
    return await service.list_recent(user.id, cursor, limit)


@router.get("/user/{user_id}", response_model=KudosList)
async def list_received(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: KudosService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    """@brief Kudos received by a user."""
    return await service.list_received(user_id, user.id, cursor, limit)


@router.delete("/{kudos_id}", status_code=204)
async def delete_kudos(
    kudos_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: KudosService = Depends(_build_service),
) -> Response:
    """@brief Delete own kudos."""
    await service.delete(kudos_id, user)
    return Response(status_code=204)
