"""
@file tag_service.py
@brief Photo tagging, tag removal, per-target tag lists and a person's
       "Tagged" feed. Post/comment tags come from @mentions (PostService).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.user import User
from app.repositories.post_enrichment import enrich_posts
from app.repositories.post_repo import PostRepository
from app.repositories.tag_repo import TagRepository
from app.services.notification_service import NotificationService

PAGE = 20


class TagService:
    """@brief Tag reads/writes with visibility checks on every target."""

    def __init__(
        self,
        repo: TagRepository,
        post_repo: PostRepository,
        notifications: NotificationService,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._posts = post_repo
        self._notify = notifications
        self._community_id = community_id

    async def _can_view(self, target_type: str, target_id: uuid.UUID, viewer: User) -> bool:
        if target_type == "post":
            return await self._posts.is_visible(target_id, viewer.id, self._community_id)
        if target_type == "comment":
            post_id = await self._repo.comment_post_id(target_id, self._community_id)
            return post_id is not None and await self._posts.is_visible(
                post_id, viewer.id, self._community_id
            )
        if target_type == "media":
            return await self._repo.media_viewable(target_id, viewer.id, self._community_id)
        return False

    async def list_for(
        self, target_type: str, target_id: uuid.UUID, viewer: User
    ) -> list[dict[str, Any]]:
        """@raises NotFoundError when the viewer can't see the target."""
        if not await self._can_view(target_type, target_id, viewer):
            raise NotFoundError(message=_("Not found"))
        tags = await self._repo.list_for_target(target_type, target_id, self._community_id)
        hidden = await self._repo.blocked_with(viewer.id, [t["user"]["id"] for t in tags])
        household = await self._repo.household_for_target(
            target_type, target_id, viewer.id, self._community_id
        )
        return [t for t in tags if t["user"]["id"] not in hidden] + household

    async def _media_tags(self, media_id: uuid.UUID, viewer: User) -> list[dict[str, Any]]:
        return await self.list_for("media", media_id, viewer)

    async def tag_household(
        self, media_id: uuid.UUID, member_id: uuid.UUID, actor: User
    ) -> list[dict[str, Any]]:
        """@brief Tag a household member/pet the actor can see in a photo they can see."""
        if not await self._repo.media_viewable(media_id, actor.id, self._community_id):
            raise NotFoundError(message=_("Photo not found"))
        # household_viewable already excludes members whose owner has a block with the actor.
        if not await self._repo.household_viewable(member_id, actor.id, self._community_id):
            raise NotFoundError(message=_("Not found"))
        owner = await self._repo.household_owner(member_id, self._community_id)
        if owner is None or not await self._repo.media_viewable(
            media_id, owner, self._community_id
        ):
            raise ValidationError(message=_("Their family can't see this photo"))
        added = await self._repo.add(
            self._community_id, "media", media_id, member_id, actor.id, subject_type="household"
        )
        if added and owner != actor.id:
            await self._notify.notify(
                user_id=owner,
                type="mention",
                payload={
                    "media_id": str(media_id),
                    "actor_name": actor.display_name,
                    "message": _("%(user)s tagged your family in a photo")
                    % {"user": actor.display_name},
                    "link": f"/app/household/{member_id}",
                },
                actor_id=actor.id,
            )
        return await self._media_tags(media_id, actor)

    async def tag_media(
        self, media_id: uuid.UUID, user_id: uuid.UUID, actor: User
    ) -> list[dict[str, Any]]:
        """
        @brief Tag ``user_id`` in a photo the actor can see. The tagged person
               must also be able to see it and have no block with the actor.
        """
        if await self._repo.media_uploader(media_id, self._community_id) is None or not (
            await self._repo.media_viewable(media_id, actor.id, self._community_id)
        ):
            raise NotFoundError(message=_("Photo not found"))
        users = await self._repo.users_by_ids(self._community_id, [user_id])
        if not users:
            raise NotFoundError(message=_("Member not found"))
        if await self._repo.blocked_with(actor.id, [user_id]) or not (
            await self._repo.media_viewable(media_id, user_id, self._community_id)
        ):
            raise ValidationError(message=_("They can't see this photo"))
        if await self._repo.add(self._community_id, "media", media_id, user_id, actor.id) and (
            user_id != actor.id
        ):
            await self._notify.notify(
                user_id=user_id,
                type="mention",
                payload={
                    "media_id": str(media_id),
                    "actor_name": actor.display_name,
                    "message": _("%(user)s tagged you in a photo") % {"user": actor.display_name},
                    "link": f"/app/members/{user_id}?tab=tagged",
                },
                actor_id=actor.id,
            )
        return await self._media_tags(media_id, actor)

    async def remove(self, tag_id: uuid.UUID, actor: User) -> None:
        """
        @brief Remove a tag: the tagged person, whoever tagged, the photo's
               uploader or an admin.
        """
        tag = await self._repo.get(tag_id, self._community_id)
        if tag is None:
            raise NotFoundError(message=_("Tag not found"))
        owner = (
            await self._repo.media_uploader(tag.target_id, self._community_id)
            if tag.target_type == "media"
            else None
        )
        keeper = (
            await self._repo.household_owner(tag.subject_id, self._community_id)
            if tag.subject_type == "household"
            else tag.subject_id
        )
        if actor.id not in (keeper, tag.tagged_by, owner) and actor.role != "admin":
            raise AuthorizationError(message=_("You can't remove this tag"))
        await self._repo.remove(tag)

    async def household_photos(
        self, member_id: uuid.UUID, viewer: User, before: datetime | None
    ) -> dict[str, Any]:
        """@brief Photos a household member/pet is tagged in, as the viewer may see them."""
        if not await self._repo.household_viewable(member_id, viewer.id, self._community_id):
            raise NotFoundError(message=_("Not found"))
        rows = await self._repo.tagged_media(
            self._community_id, member_id, viewer.id, before, PAGE, subject_type="household"
        )
        return {
            "kind": "photos",
            "media_ids": [m for m, _at in rows],
            "next_before": rows[-1][1] if len(rows) == PAGE else None,
        }

    async def tagged(
        self, subject_id: uuid.UUID, viewer: User, kind: str, before: datetime | None
    ) -> dict[str, Any]:
        """@brief Posts or photos the person is tagged in, as the viewer may see them."""
        if subject_id != viewer.id and (
            not await self._repo.users_by_ids(self._community_id, [subject_id])
            or await self._repo.blocked_with(viewer.id, [subject_id])
        ):
            raise NotFoundError(message=_("User not found"))
        if kind == "photos":
            rows = await self._repo.tagged_media(
                self._community_id, subject_id, viewer.id, before, PAGE
            )
            return {
                "kind": "photos",
                "media_ids": [m for m, _at in rows],
                "next_before": rows[-1][1] if len(rows) == PAGE else None,
            }
        return await self._posts_page(subject_id, viewer, before, "user")

    async def group_posts(
        self, subgroup_id: uuid.UUID, viewer: User, before: datetime | None
    ) -> dict[str, Any]:
        """@brief Posts that @-tag a group, as the viewer may see them."""
        return await self._posts_page(subgroup_id, viewer, before, "subgroup")

    async def _posts_page(
        self, subject_id: uuid.UUID, viewer: User, before: datetime | None, subject_type: str
    ) -> dict[str, Any]:
        prows = await self._repo.tagged_post_ids(
            self._community_id, subject_id, viewer.id, before, PAGE, subject_type
        )
        enriched = await enrich_posts(self._posts._session, [p for p, _at in prows], viewer.id)
        return {
            "kind": "posts",
            "posts": [enriched[p] for p, _at in prows if p in enriched],
            "next_before": prows[-1][1] if len(prows) == PAGE else None,
        }
