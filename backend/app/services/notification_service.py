"""
@file notification_service.py
@brief Business logic for in-app and email notifications.

Respects user notification preferences and mutes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import AppError, NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.notification import (
    NotificationList,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notifications import coalescer, dnd, registry
from app.services.notifications.api_helpers import (
    build_prefs_update,
    group_by_category,
    resolve_types,
)
from app.services.notifications.dispatcher import Dispatcher
from app.services.notifications.prefs import effective_channels
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import user_notification_dismissed

logger = structlog.get_logger(__name__)

NOTIFICATION_TYPES = (
    "mention",
    "comment",
    "reaction",
    "new_post",
    "system",
    "invite_accepted",
    "event_reminder",
    "event_rsvp",
    "gallery_activity",
    "gallery_reminder",
    "prompt",
    "prompt_summary",
    "kudos_received",
)
"""@brief Supported notification types for preference lookup."""

PREF_MAP = {
    "mention": ("notif_mention_inapp", "notif_mention_email"),
    "comment": ("notif_comment_inapp", "notif_comment_email"),
    "reaction": ("notif_reaction_inapp", "notif_reaction_email"),
    "new_post": ("notif_new_post_inapp", "notif_new_post_email"),
    "system": ("notif_system_inapp", "notif_system_email"),
    "invite_accepted": ("notif_invite_accepted_inapp", "notif_invite_accepted_email"),
    "event_reminder": ("notif_event_reminder_inapp", "notif_event_reminder_email"),
    "event_rsvp": ("notif_event_rsvp_inapp", "notif_event_rsvp_email"),
    "gallery_activity": ("notif_gallery_activity_inapp", "notif_gallery_activity_email"),
    "gallery_reminder": ("notif_gallery_activity_inapp", "notif_gallery_activity_email"),
    "birthday_reminder": ("notif_birthday_inapp", "notif_birthday_email"),
    "prompt": ("notif_prompt_inapp", "notif_prompt_email"),
    "prompt_summary": ("notif_prompt_summary_inapp", "notif_prompt_summary_email"),
    "kudos_received": ("notif_mention_inapp", "notif_mention_email"),
    "nudge_received": ("notif_nudge_inapp", "notif_nudge_email"),
    "gentle_nudge": ("notif_nudge_inapp", "notif_nudge_email"),
    "list.item": ("notif_list_item_inapp", "notif_list_item_email"),
    "list.signup": ("notif_list_signup_inapp", "notif_list_signup_email"),
    "list.completed": ("notif_list_completed_inapp", "notif_list_completed_email"),
    "list.expiring": ("notif_list_expiring_inapp", "notif_list_expiring_email"),
    "list.member": ("notif_list_member_inapp", "notif_list_member_email"),
    "data_export_ready": ("notif_system_inapp", "notif_system_email"),
    "data_export_failed": ("notif_system_inapp", "notif_system_email"),
}


class NotificationService:
    """
    @brief Service layer for notification creation and delivery.

    @param notification_repo NotificationRepository instance.
    @param settings_repo SettingsRepository instance.
    @param community_id Community scope.
    @param event_bus Optional EventBus; builds a default Dispatcher when no dispatcher given.
    @param dispatcher Optional Dispatcher (see core.dependencies.get_dispatcher).
    """

    def __init__(
        self,
        notification_repo: NotificationRepository,
        settings_repo: SettingsRepository,
        community_id: uuid.UUID,
        *,
        event_bus: EventBus | None = None,
        dispatcher: Dispatcher | None = None,
    ) -> None:
        self._notification_repo = notification_repo
        self._settings_repo = settings_repo
        self._community_id = community_id
        self._event_bus = event_bus
        if dispatcher is None:
            if event_bus is not None:
                dispatcher = Dispatcher(event_bus)
            else:
                from app.core.dependencies import get_dispatcher

                dispatcher = get_dispatcher()
        self._dispatcher = dispatcher

    async def notify(
        self,
        user_id: uuid.UUID,
        type: str,  # noqa: A002
        payload: dict[str, Any],
        actor_id: uuid.UUID | None = None,
    ) -> Notification:
        """
        @brief Validate, persist and dispatch a notification.

        @param user_id Recipient user UUID.
        @param type Registered notification type key.
        @param payload Payload validated against the type's schema.
        @param actor_id Optional actor UUID.
        @return The persisted Notification.
        @throws AppError NOTIF_TYPE_UNKNOWN or NOTIF_PREF_INVALID (400).
        """
        try:
            type_ = registry.get(type)
        except KeyError:
            raise AppError(
                code="NOTIF_TYPE_UNKNOWN",
                message=f"Unknown notification type: {type}",
                status_code=400,
            ) from None
        try:
            type_.payload_schema.model_validate(payload)
        except PydanticValidationError as exc:
            raise AppError(
                code="NOTIF_PREF_INVALID",
                message=f"Invalid payload for {type}",
                status_code=400,
                details={"errors": exc.errors(include_url=False, include_context=False)},
            ) from exc

        settings = await self._settings_repo.get_or_create(user_id, self._community_id)
        eff = effective_channels(type_, user_prefs=settings.notification_prefs or {})
        in_dnd_now = dnd.in_dnd(
            settings.dnd_schedule, settings.dnd_until, settings.dnd_timezone, datetime.now(UTC)
        )
        eff = dnd.gate_channels(eff, type_, in_dnd_now)
        notification = await self._notification_repo.upsert_grouped(
            user_id,
            type,
            payload,
            community_id=self._community_id,
            group_key=coalescer.compose_group_key(type_, payload),
            actor_id=actor_id,
            group_window_seconds=type_.group_window_seconds,
        )
        await self._dispatcher.dispatch(notification, type_, dict(eff))
        return notification

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
        *,
        type: str | None = None,  # noqa: A002
        category: str | None = None,
        unread_only: bool = False,
    ) -> NotificationList:
        """
        @brief List notifications for a user with pagination and filters.

        @param type Optional type-key filter (400 NOTIF_TYPE_UNKNOWN if unknown).
        @param category Optional registry category filter.
        @param unread_only Only unread rows.
        """
        items, next_cursor = await self._notification_repo.list_for_user(
            user_id,
            cursor=cursor,
            limit=limit,
            types=resolve_types(type, category),
            unread_only=unread_only,
        )
        return NotificationList(
            items=[NotificationResponse.model_validate(n) for n in items],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> UnreadCountResponse:
        """@brief Return unread total plus per-category breakdown."""
        per_type = await self._notification_repo.unread_counts_by_type(user_id)
        return UnreadCountResponse(
            count=sum(per_type.values()), by_category=group_by_category(per_type)
        )

    async def mark_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """@brief Mark a notification as read."""
        return await self._notification_repo.mark_read(notification_id, user_id)

    async def mark_all_read(
        self,
        user_id: uuid.UUID,
        *,
        type: str | None = None,  # noqa: A002
        category: str | None = None,
    ) -> int:
        """@brief Mark notifications read, optionally filtered by type/category."""
        return await self._notification_repo.mark_all_read(
            user_id, types=resolve_types(type, category)
        )

    async def clear_all(
        self,
        user_id: uuid.UUID,
        *,
        type: str | None = None,  # noqa: A002
        before: datetime | None = None,
    ) -> int:
        """@brief Delete a user's notifications, optionally by type and age."""
        return await self._notification_repo.delete_all_for_user(
            user_id, types=resolve_types(type, None), before=before
        )

    async def delete(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        """
        @brief Delete one notification owned by the user.

        @throws NotFoundError If missing or owned by someone else.
        """
        if not await self._notification_repo.delete_one(user_id, notification_id):
            raise NotFoundError("Notification not found")

    async def get_preferences(self, user_id: uuid.UUID) -> NotificationPreferences:
        """@brief Return v2 notification prefs + DnD + digest settings."""
        row = await self._settings_repo.get_or_create(user_id, self._community_id)
        return NotificationPreferences.model_validate(row)

    async def update_preferences(
        self, user_id: uuid.UUID, patch: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        """
        @brief Validate and apply a partial preferences update.

        @throws AppError NOTIF_TYPE_UNKNOWN / NOTIF_PREF_INVALID (400).
        """
        row = await self._settings_repo.get_or_create(user_id, self._community_id)
        data = build_prefs_update(patch, row.notification_prefs or {})
        if data:
            row = await self._settings_repo.update(user_id, data)
        return NotificationPreferences.model_validate(row)

    async def set_dnd(
        self, user_id: uuid.UUID, schedule: dict[str, Any] | None, tz: str
    ) -> NotificationPreferences:
        """@brief Set the weekly DnD schedule and its timezone."""
        await self._settings_repo.get_or_create(user_id, self._community_id)
        row = await self._settings_repo.update(
            user_id, {"dnd_schedule": schedule, "dnd_timezone": tz}
        )
        return NotificationPreferences.model_validate(row)

    async def snooze(self, user_id: uuid.UUID, until: datetime) -> None:
        """@brief Snooze external channels until ``until``."""
        await self._settings_repo.get_or_create(user_id, self._community_id)
        await self._settings_repo.update(user_id, {"dnd_until": until})

    async def clear_snooze(self, user_id: uuid.UUID) -> None:
        """@brief End any active snooze."""
        await self._settings_repo.get_or_create(user_id, self._community_id)
        await self._settings_repo.update(user_id, {"dnd_until": None})

    async def list_active(self, user_id: uuid.UUID, limit: int = 20) -> list[Notification]:
        """@brief List non-dismissed notifications, newest first."""
        return await self._notification_repo.list_active(user_id, limit)

    async def dismiss(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        """@brief Dismiss one notification owned by the user; notifies their other tabs."""
        await self._notification_repo.dismiss(user_id, notification_id)
        if self._event_bus is not None:
            await self._event_bus.emit(user_notification_dismissed(user_id, [notification_id]))

    async def dismiss_all(self, user_id: uuid.UUID) -> int:
        """@brief Dismiss all active notifications; returns count."""
        return await self._notification_repo.dismiss_all(user_id)
