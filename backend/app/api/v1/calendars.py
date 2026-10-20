"""
@file calendars.py
@brief Calendars API — list calendars visible to the current user, iCal tokens, token-gated feeds.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.calendar_repo import CalendarRepository
from app.repositories.event_repo import EventRepository
from app.schemas.calendar import CalendarResponse
from app.services.calendar_service import CalendarService
from app.services.event_service import EventService

router = APIRouter(prefix="/calendars", tags=["calendars"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> CalendarService:
    return CalendarService(
        calendar_repo=CalendarRepository(db),
        community_id=community_id,
        session=db,
    )


def _build_event_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> EventService:
    return EventService(
        event_repo=EventRepository(db),
        community_id=community_id,
        session=db,
    )


class IcalTokenResponse(BaseModel):
    """@brief Response with iCal token and feed URL."""

    token: str
    url: str


@router.get("", response_model=list[CalendarResponse])
async def list_calendars(
    user: User = Depends(get_current_user),
    service: CalendarService = Depends(_build_service),
) -> list[CalendarResponse]:
    """@brief List calendars visible to the authenticated user."""
    return await service.list_for_user(user.id)


# ── iCal tokens ──────────────────────────────────────────────────


@router.post("/me/ical-token", response_model=IcalTokenResponse)
async def issue_ical_token(
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_event_service),
) -> IcalTokenResponse:
    """@brief Issue a read-only iCal token for external subscription."""
    raw, url = await service.issue_ical_token(user.id)
    return IcalTokenResponse(token=raw, url=url)


@router.get("/feed.ics")
async def serve_ical_token_feed(
    token: str = Query(..., description="iCal token"),
    service: EventService = Depends(_build_event_service),
) -> Response:
    """@brief Serve iCal feed for a read-only token (no auth required)."""
    body = await service.serve_ical_for_token(token)
    return Response(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="nexara-events.ics"'},
    )
