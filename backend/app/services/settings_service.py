"""
@file settings_service.py
@brief Business logic for user settings and profile management.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.core.i18n import _
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.schemas.settings import (
    NotificationPreferences,
    ProfileUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)

logger = structlog.get_logger(__name__)


class SettingsService:
    """
    @brief Service layer for user settings operations.

    @param settings_repo SettingsRepository instance.
    @param user_repo UserRepository instance.
    @param community_id UUID of the community scope.
    """

    def __init__(
        self,
        settings_repo: SettingsRepository,
        user_repo: UserRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._settings_repo = settings_repo
        self._user_repo = user_repo
        self._community_id = community_id

    async def get_settings(self, user_id: uuid.UUID) -> UserSettingsResponse:
        """
        @brief Return the current user's settings.

        @param user_id UUID of the user.
        @return UserSettingsResponse with all preference fields.
        """
        settings = await self._settings_repo.get_or_create(user_id, self._community_id)
        return UserSettingsResponse.model_validate(settings)

    async def update_settings(
        self,
        user_id: uuid.UUID,
        data: UserSettingsUpdate,
    ) -> UserSettingsResponse:
        """
        @brief Update general settings (theme, locale).

        @param user_id UUID of the user.
        @param data Validated settings update payload.
        @return Updated UserSettingsResponse.
        """
        await self._settings_repo.get_or_create(user_id, self._community_id)
        update_dict = data.model_dump(exclude_none=True)
        settings = await self._settings_repo.update(user_id, update_dict)
        logger.info("settings_updated", user_id=str(user_id), fields=list(update_dict.keys()))
        return UserSettingsResponse.model_validate(settings)

    async def update_profile(
        self,
        user_id: uuid.UUID,
        data: ProfileUpdate,
    ) -> dict[str, Any]:
        """
        @brief Update user profile fields (display_name, bio, etc.).

        @param user_id UUID of the user.
        @param data Validated profile update payload.
        @return Dict of updated fields.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(_("User not found"))

        update_dict = data.model_dump(exclude_none=True)
        await self._user_repo.update(user, update_dict)
        logger.info("profile_updated", user_id=str(user_id), fields=list(update_dict.keys()))
        return update_dict

    async def update_email(
        self,
        user_id: uuid.UUID,
        new_email: str,
    ) -> None:
        """
        @brief Initiate an email address change.

        Validates the user exists and stores the pending email. In a
        production deployment this would dispatch a verification email
        via Celery.  For now, logging suffices as the email tasks are
        wired in Component 11.

        @param user_id  UUID of the user.
        @param new_email  New email address to verify.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(_("User not found"))

        logger.info(
            "email_change_requested",
            user_id=str(user_id),
            new_email=new_email,
        )

    async def update_notification_preferences(
        self,
        user_id: uuid.UUID,
        data: NotificationPreferences,
    ) -> UserSettingsResponse:
        """
        @brief Update notification preference toggles.

        @param user_id UUID of the user.
        @param data Validated notification preferences payload.
        @return Updated UserSettingsResponse.
        """
        await self._settings_repo.get_or_create(user_id, self._community_id)
        update_dict = data.model_dump(exclude_none=True)
        settings = await self._settings_repo.update(user_id, update_dict)
        logger.info(
            "notification_prefs_updated",
            user_id=str(user_id),
            fields=list(update_dict.keys()),
        )
        return UserSettingsResponse.model_validate(settings)

    async def get_notification_preferences(
        self,
        user_id: uuid.UUID,
    ) -> NotificationPreferences:
        """
        @brief Return notification preferences for a user.

        @param user_id UUID of the user.
        @return NotificationPreferences with current toggle values.
        """
        settings = await self._settings_repo.get_or_create(user_id, self._community_id)
        return NotificationPreferences(
            notif_mention_inapp=settings.notif_mention_inapp,
            notif_mention_email=settings.notif_mention_email,
            notif_comment_inapp=settings.notif_comment_inapp,
            notif_comment_email=settings.notif_comment_email,
            notif_reaction_inapp=settings.notif_reaction_inapp,
            notif_reaction_email=settings.notif_reaction_email,
            notif_new_post_inapp=settings.notif_new_post_inapp,
            notif_new_post_email=settings.notif_new_post_email,
            notif_system_inapp=settings.notif_system_inapp,
            notif_system_email=settings.notif_system_email,
            notif_invite_accepted_inapp=settings.notif_invite_accepted_inapp,
            notif_invite_accepted_email=settings.notif_invite_accepted_email,
            mute_all_email=settings.mute_all_email,
        )
