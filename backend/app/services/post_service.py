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
from app.repositories.celebration_repo import CelebrationRepository
from app.schemas.poll import PollCreate
from app.schemas.post import CelebrateIn
from app.services import post_celebrate
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
        @raises NotFoundError If post does not exist or the viewer may not read it.
        """
        if viewer_id is not None and not await self._post_repo.is_visible(
            post_id, viewer_id, self._community_id
        ):
            raise NotFoundError(_("Post not found"))
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
        private: bool = False,
        celebrate: CelebrateIn | None = None,
        is_nsfw: bool = False,
    ) -> dict[str, Any]:
        """@brief Create a new post, attach media/poll, send notifications, and publish SSE.
        @raises AuthorizationError If a non-adult marks the post NSFW.
        """
        await self._require_adult_for_nsfw(is_nsfw, user)
        celebrated = (
            await post_celebrate.resolve(
                CelebrationRepository(self._post_repo.session), self._community_id, user, celebrate
            )
            if celebrate
            else None
        )
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
            private=private,
            is_nsfw=is_nsfw,
        )

        if celebrated:
            await self._post_repo.set_celebration(
                post, celebrated.subject_type, celebrated.subject_id, celebrated.occasion
            )
            await post_celebrate.notify(self._notification, user, celebrated, post.id)

        if media_ids and self._media_attacher:
            await self._media_attacher(post.id, media_ids, user)

        if poll and self._poll_service:
            await self._poll_service.create_poll(user.id, poll, post.id)

        if reply_to_prompt_id and self._prompt_repo:
            await self._prompt_repo.refresh_response_count(reply_to_prompt_id)
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

        await self._sync_tags("post", post.id, content, user, post)

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
        await invalidate_search_cache_for_community(
            self._community_id, service="post", action="create", user_id=user.id
        )
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
        *,
        is_nsfw: bool | None = None,
    ) -> dict[str, Any]:
        """@brief Update post content and optionally the NSFW flag (author only).
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
        if is_nsfw is not None and is_nsfw != post.is_nsfw:
            # Any change (incl. un-flagging a moderated post) needs an adult.
            await self._require_adult_for_nsfw(True, user)
            post.is_nsfw = is_nsfw

        await self._post_repo.update_content(post, content)
        await self._sync_tags("post", post.id, content, user, post, fresh=False)
        await invalidate_search_cache_for_community(
            self._community_id, service="post", action="update", user_id=user.id
        )
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
        if post.reply_to_prompt_id and self._prompt_repo:
            await self._prompt_repo.refresh_response_count(post.reply_to_prompt_id)
        await invalidate_search_cache_for_community(
            self._community_id, service="post", action="delete", user_id=user.id
        )
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("post", post_id)
