"""
@file household_mentions.py
@brief @handle mentions of household members/pets in posts and comments.
       Tagged when the author can see the member and the post isn't private;
       the member's owner is notified if they can read the post, aren't the
       author and have no block with them.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.i18n import _
from app.models.user import User
from app.repositories.tag_repo import TagRepository


async def sync_household_tags(
    tags: TagRepository,
    notification: Any,
    community_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    handles: list[str],
    actor: User,
    post: Any,
) -> None:
    """@brief Make the target's household tags match ``handles`` and notify owners."""
    found = (
        []
        if post.visibility == "private"
        else await tags.household_by_handles(community_id, actor.id, handles)
    )
    new = set(
        await tags.replace_user_tags(
            community_id,
            target_type,
            target_id,
            [mid for mid, _owner in found],
            actor.id,
            subject_type="household",
        )
    )
    owners = {owner for mid, owner in found if mid in new and owner != actor.id}
    if post.subgroup_id is not None:
        owners &= set(await tags.subgroup_member_ids(post.subgroup_id, list(owners)))
    owners -= set(await tags.blocked_with(actor.id, list(owners)))
    for mid, owner in found:
        if mid in new and owner in owners:
            await notification.notify(
                user_id=owner,
                type="mention",
                payload={
                    "post_id": str(post.id),
                    "actor_name": actor.display_name,
                    "message": _("%(user)s mentioned your family in a post")
                    % {"user": actor.display_name},
                    "link": f"/app/post/{post.id}",
                },
                actor_id=actor.id,
            )
