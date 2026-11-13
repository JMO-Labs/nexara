"""
@file post_service.py
@brief Business logic for posts, comments, and reactions.

Orchestrates repository operations with notification delivery,
SSE feed_update publishing via :class:`EventBus`, and media attachment.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.plugins.hooks import HookRegistry
from app.schemas.poll import PollCreate
from app.services.activity_publish import record_activity
from app.services.post_comments import CommentsMixin
from app.services.post_reactions import ReactionsMixin
from app.services.realtime import events


class PostService(CommentsMixin, ReactionsMixin):
    """@brief Service layer for post, comment, and reaction operations."""

    async def list_feed(
        self,
        viewer_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
        subgroup_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """@brief Fetch paginated activity feed.
        @return Dict with items, cursor, and has_more.
        """
        items, next_cursor = await self._post_repo.list_feed(
            self._community_id,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=limit,
            subgroup_id=subgroup_id,
        )
        return {
            "items": items,
            "cursor": next_cursor,
            "has_more": next_cursor is not None,
        }

    async def get_post(
        self,
        post_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """@brief Fetch a single post with full enrichment.
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_post_detail(
            post_id,
            self._community_id,
            viewer_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))
        return post

    async def create_post(
        self,
        user: User,
        content: str,
        media_ids: list[uuid.UUID] | None = None,
        poll: PollCreate | None = None,
        *,
        reply_to_prompt_id: uuid.UUID | None = None,
        subgroup_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """@brief Create a new post, attach media/poll, send notifications, and publish SSE."""
        await HookRegistry.emit(
            "before_post_created",
            community_id=self._community_id,
            session=self._post_repo.session,
            user_id=user.id,
            content=content,
            subgroup_id=subgroup_id,
        )
        post = await self._post_repo.create_post(
            author_id=user.id,
            content=content,
            community_id=self._community_id,
            reply_to_prompt_id=reply_to_prompt_id,
            subgroup_id=subgroup_id,
        )

        if media_ids and self._media_attacher:
            await self._media_attacher(post.id, media_ids, user)

        if poll and self._poll_service:
            await self._poll_service.create_poll(user.id, poll, post.id)

        if reply_to_prompt_id and self._prompt_repo:
            await self._prompt_repo.increment_response_count(reply_to_prompt_id)
            prompt = await self._prompt_repo.get_by_id(reply_to_prompt_id)
            if prompt:
                if self._activity_repo is not None:
                    response_id = uuid.uuid4()
                    await record_activity(
                        self._activity_repo,
                        self._post_repo._session,
                        self._event_bus,
                        community_id=self._community_id,
                        actor_id=user.id,
                        verb="prompt.responded",
                        object_type="prompt_response",
                        object_id=response_id,
                        subgroup_id=None,
                        visibility="community",
                        target_type="prompt",
                        target_id=reply_to_prompt_id,
                        metadata={
                            "actor_name": user.display_name,
                            "object_title": prompt.title,
                        },
                    )

                if (
                    prompt.prompt_type == "interest_capture"
                    and prompt.interest_category_slug
                    and self._interest_service
                ):
                    await self._interest_service.suggest_for_user(
                        user.id, prompt.interest_category_slug, content
                    )

        enriched = await self._post_repo.get_post_detail(
            post.id,
            self._community_id,
            user.id,
        )

        await self._notify_mentions(content, user, post.id)

        if self._activity_repo is not None:
            await record_activity(
                self._activity_repo,
                self._post_repo._session,
                self._event_bus,
                community_id=self._community_id,
                actor_id=user.id,
                verb="post.created",
                object_type="post",
                object_id=post.id,
                subgroup_id=post.subgroup_id,
                visibility=post.visibility,
                target_type="subgroup" if post.subgroup_id else "community",
                target_id=post.subgroup_id or self._community_id,
                metadata={
                    "actor_name": user.display_name,
                    "object_title": post.content[:60],
                },
            )

        await HookRegistry.emit(
            "after_post_created",
            community_id=self._community_id,
            session=self._post_repo.session,
            user_id=user.id,
            post_id=post.id,
            content=content,
            subgroup_id=subgroup_id,
        )
        await invalidate_search_cache_for_community(self._community_id)
        self._enqueue_sassybot(post.id, content)

        if enriched and self._event_bus:
            await self._emit_scoped(
                events.post_created(self._target, enriched),
                post,
            )

        return enriched or {}

    async def update_post(
        self,
        post_id: uuid.UUID,
        user: User,
        content: str,
    ) -> dict[str, Any]:
        """@brief Update post content (author only).
        @raises NotFoundError If post does not exist.
        @raises AuthorizationError If user is not the author.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))
        if post.author_id != user.id:
            raise AuthorizationError(_("You can only edit your own posts"))

        await self._post_repo.update_content(post, content)
        await invalidate_search_cache_for_community(self._community_id)
        enriched = await self._post_repo.get_post_detail(
            post_id,
            self._community_id,
            user.id,
        )
        return enriched or {}

    async def delete_post(
        self,
        post_id: uuid.UUID,
        user: User,
    ) -> None:
        """@brief Soft-delete a post (author or admin only).
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_by_id(
            post_id,
            community_id=self._community_id,
        )
        if not post:
            raise NotFoundError(_("Post not found"))
        if post.author_id != user.id and user.role != "admin":
            raise AuthorizationError(_("You can only delete your own posts"))
        await self._post_repo.soft_delete(post)
        await invalidate_search_cache_for_community(self._community_id)
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("post", post_id)

