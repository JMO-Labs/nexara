"""
@file group_tag_service.py
@brief @group tags: which mentioned groups the actor may tag on a post, and
       the notification fan-out to the group's members (run from Celery).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.i18n import _
from app.models.subgroup import Subgroup
from app.models.user import User
from app.repositories.group_tag_repo import GroupTagRepository
from app.services.notification_service import NotificationService

ADMIN_ROLES = {"owner", "moderator"}


class GroupTagService:
    """@brief Rules and fan-out for @group tags."""

    def __init__(self, repo: GroupTagRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    async def existing_slugs(self, slugs: list[str]) -> set[str]:
        """@brief Which names are group slugs in this community (taggable or not)."""
        if not slugs:
            return set()
        return {g.slug for g in await self._repo.by_slugs(self._community_id, slugs)}

    async def taggable(self, slugs: list[str], actor: User, post: Any) -> list[Subgroup]:
        """
        @brief Groups among ``slugs`` the actor may tag on ``post``.
        @details Private posts tag no group; a group post may only tag its own
                 group (everyone in it can read the post); a community post
                 may tag any group. The actor must be a member (owner or
                 moderator when the group's tag_policy is "admins"); community
                 admins may tag any group.
        """
        if post.visibility == "private" or not slugs:
            return []
        groups = await self._repo.by_slugs(self._community_id, slugs)
        if post.subgroup_id is not None:
            groups = [g for g in groups if g.id == post.subgroup_id]
        elif post.visibility != "community":
            return []
        if getattr(actor, "role", None) == "admin":
            return groups
        roles = await self._repo.roles(actor.id, [g.id for g in groups])
        return [
            g
            for g in groups
            if g.id in roles and (g.tag_policy != "admins" or roles[g.id] in ADMIN_ROLES)
        ]

    async def fan_out(
        self,
        notifier: NotificationService,
        subgroup_id: uuid.UUID,
        post_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_name: str,
        on_comment: bool,
    ) -> int:
        """@brief Notify every member who can read the post; returns how many."""
        group = await self._repo.get(subgroup_id, self._community_id)
        if group is None:
            return 0
        where = _("a comment") if on_comment else _("a post")
        ids = await self._repo.recipients(subgroup_id, self._community_id, actor_id, post_id)
        for uid in ids:
            await notifier.notify(
                user_id=uid,
                type="group_tag",
                payload={
                    "post_id": str(post_id),
                    "group_id": str(subgroup_id),
                    "actor_name": actor_name,
                    "group_name": group.name,
                    "message": _("%(user)s tagged %(group)s in %(where)s")
                    % {"user": actor_name, "group": group.name, "where": where},
                    "link": f"/app/post/{post_id}",
                },
                actor_id=actor_id,
            )
        return len(ids)
