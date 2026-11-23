"""
@file trips.py
@brief Safe-arrival endpoints. Only the traveler and watchers can see a trip.
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
from app.repositories.trip_repo import TripRepository
from app.schemas.trip import TripCreate, TripExtend, TripOut
from app.services.notification_service import NotificationService
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TripService:
    """@brief Build TripService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return TripService(TripRepository(db), CommunityRepository(db), notif, cid)


@router.post("", status_code=201, response_model=TripOut)
async def start_trip(
    body: TripCreate,
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief Start a trip (422 bad time/watchers, 409 already active)."""
    return await service.start(user.id, body)


@router.get("/active", response_model=TripOut | None)
async def my_active_trip(
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief The caller's active trip or null."""
    return await service.active(user.id)


@router.get("/watching", response_model=list[TripOut])
async def watching_trips(
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief Active trips of people the caller watches."""
    return await service.watching(user.id)


@router.get("/{trip_id}", response_model=TripOut)
async def get_trip(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief One trip; 404 for anyone but the traveler and watchers."""
    return await service.get(trip_id, user.id)


@router.post("/{trip_id}/arrive", response_model=TripOut)
async def arrive(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief "Made it": tell the watchers."""
    return await service.arrive(trip_id, user.id)


@router.post("/{trip_id}/extend", response_model=TripOut)
async def extend(
    trip_id: uuid.UUID,
    body: TripExtend,
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Any:
    """@brief Move the expected arrival time (re-arms the overdue alert)."""
    return await service.extend(trip_id, user.id, body.expected_at)


@router.delete("/{trip_id}", status_code=204)
async def cancel(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TripService = Depends(_build_service),
) -> Response:
    """@brief Cancel the trip without notifying anyone."""
    await service.cancel(trip_id, user.id)
    return Response(status_code=204)
