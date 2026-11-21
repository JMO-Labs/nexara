"""
@file service.py
@brief ProfileService: a member profile as one viewer is allowed to see it.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.profile_repo import ProfileRepository
from app.schemas.profile import ProfileResponse
from app.services.profiles.visibility import FIELDS, allowed, birthday_view, effective_levels


class ProfileService:
    """@brief Applies per-field privacy to profile reads."""

    def __init__(self, repo: ProfileRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    async def view(self, user_id: uuid.UUID, viewer: User) -> ProfileResponse:
        """
        @brief Profile of ``user_id`` filtered for ``viewer``.
        @raises NotFoundError when the user is not in the community.
        """
        target = await self._repo.get_user(user_id, self._community_id)
        if target is None:
            raise NotFoundError(message=_("User not found"))
        settings = await self._repo.get_settings(target.id)
        is_self = viewer.id == target.id
        levels = effective_levels(
            settings.field_visibility if settings else None,
            settings.profile_visible_to if settings else "community",
        )
        needs_groups = not is_self and any(v == "groups" for v in levels.values())
        shares = needs_groups and await self._repo.shares_group(viewer.id, target.id)

        data: dict[str, Any] = {
            "id": target.id,
            "username": target.username,
            "display_name": target.display_name,
            "avatar_url": target.avatar_url,
            "role": target.role,
            "created_at": target.created_at,
            "last_seen_at": (
                target.last_seen_at if is_self or not settings or settings.show_last_seen else None
            ),
            "banner_media_id": target.banner_media_id,
            "birthday": birthday_view(
                target.birthday,
                is_self=is_self,
                show_to=settings.show_birthday_to if settings else "community",
                show_year=bool(settings and settings.show_birthday_year),
                viewer_is_admin=viewer.role == "admin",
            ),
        }
        for f in FIELDS:
            if allowed(levels[f], is_self=is_self, shares_group=shares):
                data[f] = getattr(target, f)
        if is_self:
            data["field_visibility"] = levels
        return ProfileResponse.model_validate(data)
