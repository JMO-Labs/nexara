"""
@file event_subscriptions.py
@brief Calendar subscription CRUD for events.

Mixed into :class:`app.services.event_service.EventService`.
"""

from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import CalendarSubscription
from app.repositories.event_repo import EventRepository
from app.schemas.event import (
    CalendarSubscriptionCreate,
    CalendarSubscriptionResponse,
    CalendarSubscriptionUpdate,
)


class EventSubscriptionsMixin:
    """@brief Subscription behaviour; relies on EventService state."""

    _repo: EventRepository
    _community_id: uuid.UUID

    # ── Subscriptions ─────────────────────────────────────────────────

    async def create_subscription(
        self, user_id: uuid.UUID, data: CalendarSubscriptionCreate, *, is_admin: bool = False
    ) -> CalendarSubscriptionResponse:
        # Reject shared_by_admin=True if not admin
        if data.shared_by_admin and not is_admin:
            raise AuthorizationError(_("Only admins can create shared subscriptions"))

        # Enforce per-user subscription cap
        count = await self._repo.count_subscriptions_for(user_id)
        settings = get_settings()
        if count >= settings.CALENDAR_SUBS_PER_USER_MAX:
            raise AppError(
                message="Subscription limit reached",
                code="subscription_limit",
            )

        sub = CalendarSubscription(
            community_id=self._community_id,
            user_id=user_id,
            name=data.name,
            color=data.color,
            source_type=data.source_type,
            source_url=data.source_url,
            visibility=data.visibility,
            shared_by_admin=data.shared_by_admin,
            sync_interval_minutes=data.sync_interval_minutes,
        )
        sub = await self._repo.create_subscription(sub)
        return CalendarSubscriptionResponse.model_validate(sub)

    async def list_subscriptions(self, user_id: uuid.UUID) -> list[CalendarSubscriptionResponse]:
        rows = await self._repo.list_subscriptions(self._community_id, user_id)
        return [CalendarSubscriptionResponse.model_validate(r) for r in rows]

    async def delete_subscription(self, sub_id: uuid.UUID, user_id: uuid.UUID) -> None:
        sub = await self._repo.get_subscription(sub_id, user_id=user_id)
        if sub is None:
            raise NotFoundError(_("Calendar subscription not found"))
        await self._repo.delete_subscription(sub_id)

    async def update_subscription(
        self, sub_id: uuid.UUID, user_id: uuid.UUID, data: CalendarSubscriptionUpdate
    ) -> CalendarSubscriptionResponse:
        """@brief Update name/url/enabled/interval of an owned subscription."""
        sub = await self._repo.get_subscription(sub_id, user_id=user_id)
        if sub is None:
            raise NotFoundError(_("Calendar subscription not found"))
        for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(sub, field, value)
        sub = await self._repo.update_subscription(sub)
        return CalendarSubscriptionResponse.model_validate(sub)
