"""
@file post_comments.py
@brief Comment listing and creation for PostService.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.services.activity_publish import record_activity
from app.services.ai.sassybot_service import wants_sassybot
from app.services.post_service_base import PostServiceBase
from app.services.realtime import events


class CommentsMixin(PostServiceBase):
    """@brief Comment listing and creation for PostService."""

    async def list_comments(
        self,
        post_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """@brief Fetch paginated comments for a post, newest first.
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))
        items, next_cursor = await self._comment_repo.list_for_post(
            post_id,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=limit,
        )
        return {
            "items": items,
            "cursor": next_cursor,
            "has_more": next_cursor is not None,
        }

    async def add_comment(
        self,
        post_id: uuid.UUID,
        user: User,
        content: str,
        parent_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """@brief Add a comment to a post and notify relevant users.
        @raises NotFoundError If post or parent comment does not exist.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))

        if parent_id:
            parent = await self._comment_repo.get_by_id(parent_id)
            if not parent or parent.post_id != post_id:
                raise NotFoundError(_("Parent comment not found"))

        comment = await self._comment_repo.create_comment(
            post_id=post_id,
            author_id=user.id,
            content=content,
            community_id=self._community_id,
            parent_id=parent_id,
        )

        await self._notify_comment_participants(
            post,
            comment,
            user,
            post_id,
            parent_id,
        )

        await self._notify_mentions(content, user, post_id)
        if wants_sassybot(content):
            self._enqueue_sassybot(post_id, content)

        comment_dict: dict[str, Any] = {
            "id": str(comment.id),
            "content": comment.content,
            "author": {
                "id": str(user.id),
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
            },
            "parent_id": str(comment.parent_id) if comment.parent_id else None,
            "created_at": comment.created_at.isoformat(),
            "replies": [],
            "reactions": [],
        }

        if self._activity_repo is not None:
            await record_activity(
                self._activity_repo,
                self._post_repo._session,
                self._event_bus,
                community_id=self._community_id,
                actor_id=user.id,
                verb="post.commented",
                object_type="comment",
                object_id=comment.id,
                subgroup_id=post.subgroup_id,
                visibility=post.visibility,
                target_type="post",
                target_id=post_id,
                metadata={
                    "actor_name": user.display_name,
                    "object_title": content[:60],
                },
            )

        if self._event_bus:
            await self._emit_scoped(
                events.comment_created(self._target, post_id, comment_dict, user.id),
                post,
            )

        return comment_dict
