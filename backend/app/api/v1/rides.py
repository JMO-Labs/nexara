"""
@file rides.py
@brief Event ride endpoints (offers, requests, join/leave, answer, cancel).
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
from app.repositories.event_repo import EventRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.ride_repo import RideRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.ride import RideAnswer, RideCreate, RideJoin, RideOut
from app.services.event_service import EventService
from app.services.notification_service import NotificationService
from app.services.ride_service import RideService

router = APIRouter(tags=["rides"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> RideService:
    """@brief Build RideService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    events = EventRepository(db)
    event_service = EventService(
        event_repo=events, community_id=cid, session=db, tag_repo=TagRepository(db)
    )
    return RideService(
        RideRepository(db), events, event_service, CommunityRepository(db), notif, cid
    )


@router.get("/events/{event_id}/rides", response_model=list[RideOut])
async def list_rides(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Any:
    """@brief Offers and requests for an event."""
    return await service.list_for_event(event_id, user.id)


@router.post("/events/{event_id}/rides/offers", status_code=201, response_model=RideOut)
async def offer_ride(
    event_id: uuid.UUID,
    body: RideCreate,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Any:
    """@brief Offer seats."""
    return await service.offer(event_id, user.id, body)


@router.post("/events/{event_id}/rides/requests", status_code=201, response_model=RideOut)
async def request_ride(
    event_id: uuid.UUID,
    body: RideCreate,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Any:
    """@brief Ask for a ride."""
    return await service.request(event_id, user.id, body)


@router.post("/rides/{ride_id}/join", response_model=RideOut)
async def join_ride(
    ride_id: uuid.UUID,
    body: RideJoin | None = None,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Any:
    """@brief Take a seat (409 RIDE_FULL / ALREADY_RIDING)."""
    return await service.join(ride_id, user.id, body.seats if body else 1)


@router.post("/rides/{ride_id}/leave", status_code=204)
async def leave_ride(
    ride_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Response:
    """@brief Give up a seat."""
    await service.leave(ride_id, user.id)
    return Response(status_code=204)


@router.post("/rides/{request_id}/answer", response_model=RideOut)
async def answer_request(
    request_id: uuid.UUID,
    body: RideAnswer,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Any:
    """@brief Take a requester onto one of my offers."""
    return await service.answer_request(request_id, body.offer_id, user.id)


@router.delete("/rides/{ride_id}", status_code=204)
async def cancel_ride(
    ride_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: RideService = Depends(_build_service),
) -> Response:
    """@brief Cancel my offer or request."""
    await service.cancel(ride_id, user.id)
    return Response(status_code=204)
