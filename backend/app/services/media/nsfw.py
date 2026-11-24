"""
@file nsfw.py
@brief Uploader NSFW flag on a photo (rules in ``services.nsfw_rules``).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.schemas.media import MediaResponse
from app.services.nsfw_rules import apply_owner_flag, require_owner_may_flag

if TYPE_CHECKING:
    from app.services.media_service import MediaService


async def precheck_flag(service: MediaService, user: User) -> None:
    """@brief Before storing an upload marked NSFW: adult + feature on, else raise."""
    await require_owner_may_flag(service._repo, service._community_id, user.id, True)


async def set_media_nsfw(
    service: MediaService, user: User, media_id: uuid.UUID, value: bool
) -> MediaResponse:
    """
    @brief Uploader sets/clears the flag (cannot clear a moderator lock).
    @throws NotFoundError missing, other community, or not visible to the user
            (NSFW for a non-adult included); AuthorizationError visible but not theirs.
    """
    repo, tags = service._repo, service._tag_repo
    if tags is None:  # wired by the route's DI (``_build_service``)
        raise RuntimeError("MediaService needs tag_repo to change NSFW flags")
    media = await repo.get(media_id)
    if media is None or media.community_id != service._community_id:
        raise NotFoundError(_("Media not found"))
    if media.uploader_id != user.id and not await tags.media_viewable(
        media_id, user.id, service._community_id
    ):
        raise NotFoundError(_("Media not found"))
    if media.uploader_id != user.id:
        raise AuthorizationError(_("Only the uploader can change this photo"))
    if value != media.is_nsfw:
        await require_owner_may_flag(repo, service._community_id, user.id, value)
        apply_owner_flag(media, value)
        await repo.session.flush()
    return MediaResponse.model_validate(media)
