"""
@file post_service.py
@brief Business logic for posts, comments, and reactions.

Orchestrates repository operations with notification delivery,
SSE feed_update publishing via :class:`EventBus`, and media attachment.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.post import Post
from app.models.user import User
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.schemas.poll import PollCreate
from app.schemas.post import ReactionResponse
from app.services.notification_service import NotificationService
from app.services.poll_service import PollService
from app.services.realtime import events
from app.services.realtime.event_bus import EventBus

logger = structlog.get_logger(__name__)


class PostService:
    """@brief Service layer for post, comment, and reaction operations."""

    def __init__(
        self,
        post_repo: PostRepository,
        comment_repo: CommentRepository,
        reaction_repo: ReactionRepository,
        notification_service: NotificationService,
        community_id: uuid.UUID,
        *,
        event_bus: EventBus | None = None,
        media_attacher: Callable[[uuid.UUID, list[uuid.UUID], User], Awaitable[None]] | None = None,
        poll_service: PollService | None = None,
        prompt_repo: PromptRepository | None = None,
        interest_service: Any | None = None,
    ) -> None:
        self._post_repo = post_repo
        self._comment_repo = comment_repo
        self._reaction_repo = reaction_repo
        self._notification = notification_service
        self._community_id = community_id
        self._event_bus = event_bus
        self._media_attacher = media_attacher
        self._poll_service = poll_service
        self._prompt_repo = prompt_repo
        self._interest_service = interest_service

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
            if (
                prompt
                and prompt.prompt_type == "interest_capture"
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

        await self._notification.notify_mentions(
            content,
            user,
            post.id,
            self._post_repo._session,
        )

        if enriched and self._event_bus:
            await self._event_bus.emit(
                events.post_created(self._community_id, enriched),
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

        await self._notification.notify_mentions(
            content,
            user,
            post_id,
            self._post_repo._session,
        )

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

        if self._event_bus:
            await self._event_bus.emit(
                events.comment_created(
                    self._community_id,
                    post_id,
                    comment_dict,
                    user.id,
                ),
            )

        return comment_dict

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

        await self._publish_reaction_event(
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

        await self._publish_reaction_event(
            post_id,
            "comment",
            comment_id,
            emoji,
            count,
            action,
            user.id,
        )

        return ReactionResponse(action=action, emoji=emoji, count=count)

    async def _publish_reaction_event(
        self,
        post_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        emoji: str,
        count: int,
        action: str,
        user_id: uuid.UUID,
    ) -> None:
        """@brief Publish a reaction_toggled SSE event via the event bus."""
        if not self._event_bus:
            return
        await self._event_bus.emit(
            events.reaction_toggled(
                self._community_id,
                post_id,
                target_type,
                target_id,
                emoji,
                count,
                action,
                user_id,
            ),
        )

    async def _notify_comment_participants(
        self,
        post: Post,
        comment: Any,
        user: User,
        post_id: uuid.UUID,
        parent_id: uuid.UUID | None,
    ) -> None:
        """@brief Notify post author and parent comment author about a new comment."""
        link = f"/app/post/{post_id}"
        base_payload = {
            "post_id": str(post_id),
            "comment_id": str(comment.id),
            "link": link,
        }

        if post.author_id != user.id:
            await self._notification.notify(
                user_id=post.author_id,
                type="comment",
                payload={
                    **base_payload,
                    "message": _("%(user)s commented on your post") % {"user": user.display_name},
                },
                actor_id=user.id,
            )

        if parent_id:
            parent = await self._comment_repo.get_by_id(parent_id)
            if parent and parent.author_id and parent.author_id != user.id:
                await self._notification.notify(
                    user_id=parent.author_id,
                    type="comment",
                    payload={
                        **base_payload,
                        "message": _("%(user)s replied to your comment")
                        % {"user": user.display_name},
                    },
                    actor_id=user.id,
                )
