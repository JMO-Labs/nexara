"""
@file nsfw_rules.py
@brief Who may set or clear the NSFW flag on a post, album or photo.

Authors/owners: must be effective adults; setting needs the ``nsfw`` feature on;
they may set the flag any time but clear it only when no moderator locked it.
Moderators (group owner/moderator for group content, community admins for all):
setting locks the flag, clearing unlocks it.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, AuthorizationError
from app.core.i18n import _


async def require_owner_may_flag(
    repo: Any, community_id: uuid.UUID, user_id: uuid.UUID, value: bool
) -> None:
    """
    @brief Gate an author/owner flag change (create or update).
    @param repo Any BaseRepository (``viewer_adult``, ``feature_on``).
    @throws AppError FEATURE_DISABLED (404) when setting with the feature off.
    @throws AuthorizationError when the user is not an effective adult.
    """
    if value and not await repo.feature_on(community_id, "nsfw"):
        raise AppError(code="FEATURE_DISABLED", message="Feature is disabled", status_code=404)
    if not await repo.viewer_adult(user_id):
        raise AuthorizationError(_("Only adults can mark content as NSFW"))


def apply_owner_flag(entity: Any, value: bool | None) -> bool:
    """
    @brief Author/owner change; call ``require_owner_may_flag`` first.
    @return True when the flag changed.
    @throws AuthorizationError when clearing a moderator-locked flag.
    """
    if value is None or value == entity.is_nsfw:
        return False
    if not value and entity.nsfw_locked:
        raise AuthorizationError(_("A moderator marked this NSFW"))
    entity.is_nsfw = value
    return True


def apply_moderator_flag(entity: Any, value: bool) -> None:
    """@brief Moderator change: set locks the flag, clear unlocks it."""
    entity.is_nsfw = value
    entity.nsfw_locked = value
