"""
@file event_rsvp.py
@brief RSVP and contribution-slot behaviour for events.

Mixed into :class:`app.services.event_service.EventService`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import Event
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.event_repo import EventRepository
from app.schemas.event import (
    ContributionClaim,
    ContributionSlot,
    EventResponse,
    RSVPRequest,
    RSVPResponse,
)
from app.services.activity_publish import record_activity

logger = structlog.get_logger(__name__)

DEFAULT_RSVP_LABELS: dict[str, str] = {
    "attending": "Attending",
    "maybe": "Maybe",
    "declined": "Declined",
}


class EventRsvpMixin:
    """@brief RSVP + contribution behaviour; relies on EventService state/helpers."""

    _repo: EventRepository
    _community_id: uuid.UUID
    _session: AsyncSession
    _notifications: Any | None
    _activity_repo: ActivityRepository | None

    if TYPE_CHECKING:

        async def _can_view(self, event: Event, user_id: uuid.UUID) -> bool: ...
        def _slots_from_db(self, raw: list[dict[str, Any]] | None) -> list[ContributionSlot]: ...
        def _slots_to_dicts(self, slots: list[ContributionSlot]) -> list[dict[str, Any]]: ...
        async def _build_response(
            self,
            event: Event,
            *,
            user_id: uuid.UUID | None = None,
            gallery_id: uuid.UUID | None = None,
            slugs: dict[uuid.UUID, str] | None = None,
        ) -> EventResponse: ...

    # ── RSVP ──────────────────────────────────────────────────────────

    async def _actor_name(self, user_id: uuid.UUID) -> str:
        """@brief Display name of ``user_id`` for notification payloads."""
        user = await self._session.get(User, user_id)
        return str(user.display_name) if user is not None else _("Someone")

    async def rsvp(
        self, event_id: uuid.UUID, user_id: uuid.UUID, data: RSVPRequest
    ) -> RSVPResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot RSVP to this event"))

        labels = dict(event.rsvp_labels) if event.rsvp_labels else dict(DEFAULT_RSVP_LABELS)
        if data.status not in labels:
            raise AppError(
                code="INVALID_RSVP_STATUS",
                message=_("RSVP status is not allowed for this event"),
                status_code=400,
            )

        att = await self._repo.upsert_attendance(
            event_id=event_id,
            user_id=user_id,
            community_id=self._community_id,
            status=data.status,
            note=data.note,
        )

        if self._notifications and event.author_id != user_id:
            try:
                await self._notifications.notify(
                    user_id=event.author_id,
                    type="event_rsvp",
                    payload={
                        "event_id": str(event.id),
                        "status": data.status,
                        "actor_name": await self._actor_name(user_id),
                        "event_title": event.title,
                        "message": _("Someone RSVP'd to your event"),
                        "link": f"/app/events/{event.id}",
                    },
                    actor_id=user_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rsvp_notify_failed", error=str(exc))

        if self._activity_repo is not None:
            user_result = await self._session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            user_name = user.display_name if user else "Unknown"

            rsvp_id = att.id if hasattr(att, "id") else uuid.uuid4()
            await record_activity(
                self._activity_repo,
                self._session,
                None,
                community_id=self._community_id,
                actor_id=user_id,
                verb="event.rsvp",
                object_type="rsvp",
                object_id=rsvp_id,
                subgroup_id=event.subgroup_id,
                visibility=event.visibility,
                target_type="event",
                target_id=event_id,
                metadata={
                    "actor_name": user_name,
                    "object_title": event.title,
                },
            )

        return RSVPResponse.model_validate(att)

    async def list_rsvps(self, event_id: uuid.UUID, user_id: uuid.UUID) -> list[RSVPResponse]:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot view this event"))
        records = await self._repo.list_attendance(event_id)
        return [RSVPResponse.model_validate(r) for r in records]

    async def cancel_rsvp(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        await self._repo.remove_attendance(event_id, user_id)

    # ── Contributions ─────────────────────────────────────────────────

    async def claim_contribution(
        self,
        event_id: uuid.UUID,
        slot_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ContributionClaim,
    ) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))
        if not await self._can_view(event, user_id):
            raise AuthorizationError(_("You cannot claim contributions on this event"))

        slots = self._slots_from_db(event.contribution_slots)
        target = next((s for s in slots if s.id == slot_id), None)
        if target is None:
            raise NotFoundError(_("Contribution slot not found"))

        remaining = target.quantity_needed - target.quantity_claimed
        if data.quantity > remaining:
            raise AppError(
                code="SLOT_FULL",
                message=_("Not enough remaining capacity on this slot"),
                status_code=400,
            )
        target.quantity_claimed += data.quantity
        if user_id not in target.claimed_by:
            target.claimed_by.append(user_id)

        event = await self._repo.update(
            event,
            {
                "contribution_slots": self._slots_to_dicts(slots),
                "updated_at": datetime.now(UTC),
            },
        )
        return await self._build_response(event, user_id=user_id)

    async def unclaim_contribution(
        self, event_id: uuid.UUID, slot_id: uuid.UUID, user_id: uuid.UUID
    ) -> EventResponse:
        event = await self._repo.get_by_id(event_id, community_id=self._community_id)
        if event is None:
            raise NotFoundError(_("Event not found"))

        slots = self._slots_from_db(event.contribution_slots)
        target = next((s for s in slots if s.id == slot_id), None)
        if target is None:
            raise NotFoundError(_("Contribution slot not found"))

        if user_id in target.claimed_by:
            target.claimed_by.remove(user_id)
            target.quantity_claimed = max(0, target.quantity_claimed - 1)

        event = await self._repo.update(
            event,
            {
                "contribution_slots": self._slots_to_dicts(slots),
                "updated_at": datetime.now(UTC),
            },
        )
        return await self._build_response(event, user_id=user_id)
