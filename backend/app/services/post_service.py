"""
@file post_service.py
@brief Business logic for posts, comments, and reactions.

Orchestrates repository operations with notification delivery,
SSE feed_update publishing, and media attachment.
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
from app.repositories.post_repo import CommentRepository, PostRepository, ReactionRepository
from app.schemas.post import (
    ReactionResponse,
)
from app.services.notification_service import NotificationService

logger = structlog.get_logger(__name__)


class PostService:
    """
    @brief Service layer for post, comment, and reaction operations.

    @param post_repo PostRepository instance.
    @param comment_repo CommentRepository instance.
    @param reaction_repo ReactionRepository instance.
    @param notification_service NotificationService for triggering notifications.
    @param community_id Community scope UUID.
    @param feed_publisher Optional coroutine to publish feed_update SSE events.
    @param media_attacher Optional coroutine to attach media to a post.
    """

    def __init__(
        self,
        post_repo: PostRepository,
        comment_repo: CommentRepository,
        reaction_repo: ReactionRepository,
        notification_service: NotificationService,
        community_id: uuid.UUID,
        *,
        feed_publisher: Callable[[uuid.UUID, dict[str, Any]], Awaitable[int]] | None = None,
        media_attacher: Callable[[uuid.UUID, list[uuid.UUID], User], Awaitable[None]] | None = None,
    ) -> None:
        self._post_repo = post_repo
        self._comment_repo = comment_repo
        self._reaction_repo = reaction_repo
        self._notification = notification_service
        self._community_id = community_id
        self._feed_publisher = feed_publisher
        self._media_attacher = media_attacher

    async def list_feed(
        self,
        viewer_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        @brief Fetch paginated activity feed.

        @param viewer_id Current user for block filter and reaction state.
        @param cursor Opaque cursor for pagination.
        @param limit Number of posts per page.
        @return Dict with items, cursor, and has_more.
        """
        items, next_cursor = await self._post_repo.list_feed(
            self._community_id,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=limit,
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
        """
        @brief Fetch a single post with full enrichment.

        @param post_id Post UUID.
        @param viewer_id Current user for reaction state.
        @return Enriched post dict.
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_post_detail(post_id, self._community_id, viewer_id)
        if not post:
            raise NotFoundError(_("Post not found"))
        return post

    async def create_post(
        self,
        user: User,
        content: str,
        media_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        """
        @brief Create a new post, attach media, send notifications, and publish SSE.

        @param user The authoring user.
        @param content Markdown content.
        @param media_ids Optional media UUIDs to attach.
        @return Enriched post dict.
        """
        post = await self._post_repo.create_post(
            author_id=user.id,
            content=content,
            community_id=self._community_id,
        )

        if media_ids and self._media_attacher:
            await self._media_attacher(post.id, media_ids, user)

        enriched = await self._post_repo.get_post_detail(post.id, self._community_id, user.id)

        mentions = NotificationService.detect_mentions(content)
        await self._notify_mentions(mentions, user, post)

        if enriched and self._feed_publisher:
            msg = {
                "type": "feed_update",
                "payload": {"event": "created", "post": enriched},
            }
            await self._feed_publisher(self._community_id, msg)

        return enriched or {}

    async def update_post(
        self,
        post_id: uuid.UUID,
        user: User,
        content: str,
    ) -> dict[str, Any]:
        """
        @brief Update post content. Only the author may edit.

        @param post_id Post UUID.
        @param user Requesting user.
        @param content New markdown content.
        @return Enriched post dict.
        @raises NotFoundError If post does not exist.
        @raises AuthorizationError If user is not the author.
        """
        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
        if not post:
            raise NotFoundError(_("Post not found"))
        if post.author_id != user.id:
            raise AuthorizationError(_("You can only edit your own posts"))

        await self._post_repo.update_content(post, content)
        enriched = await self._post_repo.get_post_detail(post_id, self._community_id, user.id)
        return enriched or {}

    async def delete_post(
        self,
        post_id: uuid.UUID,
        user: User,
    ) -> None:
        """
        @brief Soft-delete a post. Only the author or an admin may delete.

        @param post_id Post UUID.
        @param user Requesting user.
        @raises NotFoundError If post does not exist.
        @raises AuthorizationError If user is not author or admin.
        """
        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
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
        """
        @brief Fetch paginated comments for a post, newest first.

        @param post_id Post UUID.
        @param viewer_id Current user for block filter.
        @param cursor Opaque pagination cursor.
        @param limit Comments per page.
        @return Dict with items, cursor, and has_more.
        """
        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
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
        """
        @brief Add a comment to a post and notify relevant users.

        @param post_id Post UUID.
        @param user Comment author.
        @param content Comment text.
        @param parent_id Optional parent comment UUID.
        @return Comment dict.
        @raises NotFoundError If post or parent comment does not exist.
        """
        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
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

        if post.author_id != user.id:
            await self._notification.notify(
                user_id=post.author_id,
                type="comment",
                payload={
                    "post_id": str(post_id),
                    "comment_id": str(comment.id),
                    "message": _("%(user)s commented on your post") % {"user": user.display_name},
                    "link": f"/app/post/{post_id}",
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
                        "post_id": str(post_id),
                        "comment_id": str(comment.id),
                        "message": _("%(user)s replied to your comment")
                        % {"user": user.display_name},
                        "link": f"/app/post/{post_id}",
                    },
                    actor_id=user.id,
                )

        mentions = NotificationService.detect_mentions(content)
        await self._notify_mentions(mentions, user, post)

        return {
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
        }

    async def toggle_reaction(
        self,
        post_id: uuid.UUID,
        user: User,
        emoji: str,
    ) -> ReactionResponse:
        """
        @brief Toggle a reaction on a post.

        @param post_id Post UUID.
        @param user Reacting user.
        @param emoji Emoji string.
        @return ReactionResponse with action, emoji, and count.
        @raises NotFoundError If post does not exist.
        """
        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
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

        return ReactionResponse(action=action, emoji=emoji, count=count)

    async def _notify_mentions(
        self,
        usernames: list[str],
        actor: User,
        post: Post,
    ) -> None:
        """
        @brief Send mention notifications for @username references.

        @param usernames List of mentioned usernames.
        @param actor User who authored the content.
        @param post The post containing the mentions.
        """
        if not usernames:
            return

        from sqlalchemy import select as sa_select

        from app.models.user import User as UserModel

        session = self._post_repo._session
        stmt = sa_select(UserModel).where(
            UserModel.username.in_(usernames),
            UserModel.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        mentioned_users = result.scalars().all()

        for mentioned in mentioned_users:
            if mentioned.id == actor.id:
                continue
            await self._notification.notify(
                user_id=mentioned.id,
                type="mention",
                payload={
                    "post_id": str(post.id),
                    "message": _("%(user)s mentioned you in a post") % {"user": actor.display_name},
                    "link": f"/app/post/{post.id}",
                },
                actor_id=actor.id,
            )
