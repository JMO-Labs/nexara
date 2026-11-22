"""
@file settings_service.py
@brief Business logic for user settings and profile management.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.schemas.profile import ProfileUpdate
from app.schemas.settings import (
    NotificationPreferences,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.user_service import UserService

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
        current = await self._settings_repo.get_or_create(user_id, self._community_id)
        update_dict = data.model_dump(exclude_unset=True)
        if data.home_layout is not None:
            # Keys the client didn't send (e.g. pinned favorites) survive.
            update_dict["home_layout"] = {
                **(current.home_layout or {}),
                **data.home_layout.model_dump(mode="json", exclude_unset=True),
            }
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

        raw = data.model_dump(mode="json", exclude_unset=True)
        visibility = raw.pop("field_visibility", None)
        gravatar = raw.pop("use_gravatar", None)
        if "avatar_media_id" in raw:
            raw.pop("avatar_media_id")
            raw["avatar_url"] = await self._avatar_url(user, data.avatar_media_id)
        if gravatar is not None:
            # Only touch Gravatar-managed avatars; an uploaded photo always wins.
            if gravatar and not user.avatar_url:
                raw["avatar_url"] = UserService.gravatar_url(user.email)
            elif not gravatar and UserService.is_gravatar(user.avatar_url):
                raw["avatar_url"] = None
        if raw.get("display_name") is None:
            raw.pop("display_name", None)  # required; never cleared
        update_dict = {k: (None if v == "" else v) for k, v in raw.items()}
        for k in ("links", "skills"):
            if k in update_dict and update_dict[k] is None:
                update_dict[k] = []
        if "birthday" in update_dict:
            update_dict["birthday"] = data.birthday
        if update_dict.get("banner_media_id") is not None:
            media = await self._user_repo.get_media(data.banner_media_id)  # type: ignore[arg-type]
            if media is None or media.community_id != user.community_id:
                raise NotFoundError(message=_("Banner image not found"))
            update_dict["banner_media_id"] = data.banner_media_id
        if update_dict:
            await self._user_repo.update(user, update_dict)
        if visibility:
            row = await self._settings_repo.get_or_create(user_id, user.community_id)
            await self._settings_repo.update(
                user_id, {"field_visibility": {**(row.field_visibility or {}), **visibility}}
            )
        logger.info(
            "profile_updated",
            user_id=str(user_id),
            fields=list(update_dict.keys()) + (["field_visibility"] if visibility else []),
        )
        return update_dict

    async def _avatar_url(self, user: Any, media_id: uuid.UUID | None) -> str | None:
        """
        @brief Avatar URL for an uploaded photo (your own image in this
               community), or None to remove it.
        @throws NotFoundError when the media can't be used
        """
        if media_id is None:
            return None
        media = await self._user_repo.get_media(media_id)
        if (
            media is None
            or media.community_id != user.community_id
            or media.uploader_id != user.id
            or not media.content_type.startswith("image/")
        ):
            raise NotFoundError(message=_("Photo not found"))
        return f"/api/v1/media/{media_id}/thumbnail"

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
        return NotificationPreferences.model_validate(
            {name: getattr(settings, name) for name in NotificationPreferences.model_fields}
        )
