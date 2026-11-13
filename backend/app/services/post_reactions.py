"""
@file post_reactions.py
@brief Reaction toggling for PostService.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.schemas.post import ReactionResponse
from app.services.activity_publish import record_activity
from app.services.post_service_base import PostServiceBase


class ReactionsMixin(PostServiceBase):
    """@brief Reaction toggling for PostService."""

    async def toggle_reaction(
        self,
        post_id: uuid.UUID,
        user: User,
        emoji: str,
    ) -> ReactionResponse:
        """@brief Toggle a reaction on a post.
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))

        action, count = await self._reaction_repo.toggle(
            user_id=user.id,
            target_type="post",
            target_id=post_id,
            emoji=emoji,
            community_id=self._community_id,
        )

        if action == "added" and post.author_id != user.id:
            await self._notification.notify(
                user_id=post.author_id,
                type="reaction",
                payload={
                    "post_id": str(post_id),
                    "emoji": emoji,
                    "message": _("%(user)s reacted to your post") % {"user": user.display_name},
                    "link": f"/app/post/{post_id}",
                },
                actor_id=user.id,
            )

        if action == "added" and self._activity_repo is not None:
            reaction_id = uuid.uuid4()
            await record_activity(
                self._activity_repo,
                self._post_repo._session,
                self._event_bus,
                community_id=self._community_id,
                actor_id=user.id,
                verb="post.reacted",
                object_type="reaction",
                object_id=reaction_id,
                subgroup_id=post.subgroup_id,
                visibility=post.visibility,
                target_type="post",
                target_id=post_id,
                metadata={
                    "actor_name": user.display_name,
                    "object_title": emoji,
                },
            )

        await self._publish_reaction_event(
            post,
            post_id,
            "post",
            post_id,
            emoji,
            count,
            action,
            user.id,
        )

        return ReactionResponse(action=action, emoji=emoji, count=count)

    async def toggle_comment_reaction(
        self,
        post_id: uuid.UUID,
        comment_id: uuid.UUID,
        user: User,
        emoji: str,
    ) -> ReactionResponse:
        """@brief Toggle a reaction on a comment.
        @raises NotFoundError If post or comment does not exist.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))

        comment = await self._comment_repo.get_by_id(comment_id)
        if not comment or comment.post_id != post_id:
            raise NotFoundError(_("Comment not found"))

        action, count = await self._reaction_repo.toggle(
            user_id=user.id,
            target_type="comment",
            target_id=comment_id,
            emoji=emoji,
            community_id=self._community_id,
        )

        if action == "added" and comment.author_id and comment.author_id != user.id:
            await self._notification.notify(
                user_id=comment.author_id,
                type="reaction",
                payload={
                    "post_id": str(post_id),
                    "comment_id": str(comment_id),
                    "emoji": emoji,
                    "message": _("%(user)s reacted to your comment") % {"user": user.display_name},
                    "link": f"/app/post/{post_id}",
                },
                actor_id=user.id,
            )

        if action == "added" and self._activity_repo is not None:
            reaction_id = uuid.uuid4()
            await record_activity(
                self._activity_repo,
                self._post_repo._session,
                self._event_bus,
                community_id=self._community_id,
                actor_id=user.id,
                verb="post.reacted",
                object_type="reaction",
                object_id=reaction_id,
                subgroup_id=post.subgroup_id,
                visibility=post.visibility,
                target_type="comment",
                target_id=comment_id,
                metadata={
                    "actor_name": user.display_name,
                    "object_title": emoji,
                },
            )

        await self._publish_reaction_event(
            post,
            post_id,
            "comment",
            comment_id,
            emoji,
            count,
            action,
            user.id,
        )

        return ReactionResponse(action=action, emoji=emoji, count=count)
