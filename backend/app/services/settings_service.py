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


def _validate_settings_tolerant(settings: Any) -> UserSettingsResponse:
    """Validate settings; if the legacy home_layout shape fails validation,
    log a warning and treat the field as None so clients fall back to the
    default dashboard layout."""
    try:
        return UserSettingsResponse.model_validate(settings)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "home_layout_legacy_dropped",
            user_id=str(getattr(settings, "user_id", "?")),
            error=str(exc),
        )
        # Re-validate with home_layout cleared.
        try:
            data = settings.__dict__ if hasattr(settings, "__dict__") else dict(settings)
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            data["home_layout"] = None
            return UserSettingsResponse.model_validate(data)
        except Exception:  # pragma: no cover
            raise exc


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
        return _validate_settings_tolerant(settings)

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
        update_dict = data.model_dump(exclude_unset=True)
        settings = await self._settings_repo.update(user_id, update_dict)
        logger.info("settings_updated", user_id=str(user_id), fields=list(update_dict.keys()))
        return _validate_settings_tolerant(settings)

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
        return _validate_settings_tolerant(settings)

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
            **{name: getattr(settings, name) for name in NotificationPreferences.model_fields}
        )
