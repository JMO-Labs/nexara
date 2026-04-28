"""
@file events.py
@brief Events API endpoints — CRUD, RSVP, contributions, iCal, subscriptions.

All endpoints require authentication.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.event_repo import EventRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.event import (
    CalendarSubscriptionCreate,
    CalendarSubscriptionResponse,
    ContributionClaim,
    EventCreate,
    EventList,
    EventResponse,
    EventUpdate,
    RSVPRequest,
    RSVPResponse,
)
from app.schemas.gallery import (
    GalleryItemBulkCreate,
    GalleryItemResponse,
    GalleryResponse,
)
from app.services.event_service import EventService
from app.services.gallery_service import GalleryService
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> EventService:
    """@brief Build EventService with notification + DB deps."""
    notif = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        event_bus=event_bus,
    )
    return EventService(
        event_repo=EventRepository(db),
        community_id=community_id,
        session=db,
        notification_service=notif,
    )


def _build_gallery_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> GalleryService:
    """@brief Build GalleryService with DB deps."""
    return GalleryService(
        gallery_repo=GalleryRepository(db),
        community_id=community_id,
        session=db,
    )


# ── CRUD ──────────────────────────────────────────────────────────


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    body: EventCreate,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Create a new event."""
    return await service.create_event(user.id, body)


@router.get("", response_model=EventList)
async def list_events(
    start: datetime | None = Query(None, description="Window start (UTC)"),
    end: datetime | None = Query(None, description="Window end (UTC)"),
    cursor: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventList:
    """@brief List events overlapping a window. Defaults to next 90 days."""
    now = datetime.now(UTC)
    s = start or now - timedelta(days=7)
    e = end or now + timedelta(days=90)
    return await service.list_events(user.id, s, e, cursor=cursor, limit=limit)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Get a single event."""
    return await service.get_event(event_id, user.id)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Update an event (organizer only)."""
    return await service.update_event(event_id, user.id, body)


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete an event (organizer only)."""
    await service.delete_event(event_id, user.id)
    return MessageResponse(message=_("Event deleted"))


# ── RSVP ──────────────────────────────────────────────────────────


@router.post("/{event_id}/rsvp", response_model=RSVPResponse)
async def rsvp(
    event_id: uuid.UUID,
    body: RSVPRequest,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> RSVPResponse:
    """@brief Cast or update an RSVP."""
    return await service.rsvp(event_id, user.id, body)


@router.get("/{event_id}/rsvps", response_model=list[RSVPResponse])
async def list_rsvps(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> list[RSVPResponse]:
    """@brief List RSVPs for an event."""
    return await service.list_rsvps(event_id, user.id)


@router.delete("/{event_id}/rsvp", response_model=MessageResponse)
async def cancel_rsvp(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> MessageResponse:
    """@brief Cancel a user's RSVP."""
    await service.cancel_rsvp(event_id, user.id)
    return MessageResponse(message=_("RSVP cancelled"))


# ── Contributions ─────────────────────────────────────────────────


@router.post("/{event_id}/contributions/{slot_id}/claim", response_model=EventResponse)
async def claim_contribution(
    event_id: uuid.UUID,
    slot_id: uuid.UUID,
    body: ContributionClaim,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Claim a contribution slot."""
    return await service.claim_contribution(event_id, slot_id, user.id, body)


@router.delete("/{event_id}/contributions/{slot_id}/claim", response_model=EventResponse)
async def unclaim_contribution(
    event_id: uuid.UUID,
    slot_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Release a claimed contribution slot."""
    return await service.unclaim_contribution(event_id, slot_id, user.id)


# ── iCal export ───────────────────────────────────────────────────


@router.get("/{event_id}/ical")
async def export_event_ical(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> Response:
    """@brief Export a single event as .ics."""
    body = await service.export_event_ical(event_id, user.id)
    return Response(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}.ics"'},
    )


@router.get("/feed.ics")
async def export_feed_ical(
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> Response:
    """@brief Export the user's full event feed as .ics."""
    body = await service.export_feed_ical(user.id)
    return Response(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="nexara-events.ics"'},
    )


# ── Event galleries ──────────────────────────────────────────────


@router.get("/{event_id}/gallery", response_model=GalleryResponse)
async def get_event_gallery(
    event_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_gallery_service),
) -> GalleryResponse:
    """@brief Get or create the auto-gallery for an event."""
    result = await service.ensure_event_gallery(event_id, user.id, "Event Gallery")
    return result


@router.post("/{event_id}/gallery/contribute", response_model=list[GalleryItemResponse])
async def contribute_to_event_gallery(
    event_id: uuid.UUID,
    body: GalleryItemBulkCreate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_gallery_service),
) -> list[GalleryItemResponse]:
    """@brief Add media items to an event's gallery."""
    gallery = await service.ensure_event_gallery(event_id, user.id, "Event Gallery")
    result = await service.bulk_add_items(gallery.id, user.id, body)
    return result


# ── Subscriptions ─────────────────────────────────────────────────

subs_router = APIRouter(prefix="/calendar-subscriptions", tags=["calendar-subscriptions"])


@subs_router.post("", response_model=CalendarSubscriptionResponse, status_code=201)
async def create_subscription(
    body: CalendarSubscriptionCreate,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> CalendarSubscriptionResponse:
    """@brief Create an external calendar subscription."""
    return await service.create_subscription(user.id, body)


@subs_router.get("", response_model=list[CalendarSubscriptionResponse])
async def list_subscriptions(
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> list[CalendarSubscriptionResponse]:
    """@brief List the current user's subscriptions."""
    return await service.list_subscriptions(user.id)


@subs_router.delete("/{sub_id}", response_model=MessageResponse)
async def delete_subscription(
    sub_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete a calendar subscription."""
    await service.delete_subscription(sub_id, user.id)
    return MessageResponse(message=_("Subscription deleted"))


@router.patch("/{event_id}/occurrences/{iso_start}", response_model=EventResponse)
async def update_occurrence(
    event_id: uuid.UUID,
    iso_start: str,
    scope: str = Query("this", regex="^(this|this_and_following|all)$"),
    data: EventUpdate = None,
    user: User = Depends(get_current_user),
    service: EventService = Depends(_build_service),
) -> EventResponse:
    """@brief Update a single occurrence of a recurring event.

    @param event_id ID of the recurring event.
    @param iso_start ISO 8601 datetime of the occurrence (e.g. '2026-05-08T18:00:00Z').
    @param scope Update scope: 'this', 'this_and_following', or 'all'.
    @param data Fields to update (title, description, etc.).
    @return The modified or new event.
    """
    try:
        occurrence_dt = datetime.fromisoformat(iso_start.replace("Z", "+00:00"))
    except ValueError as exc:
        from app.core.exceptions import AppError

        raise AppError(
            code="INVALID_ISO_START",
            message=_("Invalid ISO 8601 datetime format"),
            status_code=400,
        ) from exc

    payload = data.model_dump(exclude_unset=True) if data else {}
    result = await service.update_occurrence(
        event_id,
        occurrence_dt,
        scope,  # type: ignore[arg-type]
        payload,
    )
    return await service._build_response(result, user_id=user.id)
