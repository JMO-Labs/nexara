"""
@file post_service_base.py
@brief Shared state and helpers for the post service mixins.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from sqlalchemy import select

from app.core.i18n import _
from app.models.post import Post
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.services import mentions
from app.services.ai.sassybot_service import wants_sassybot
from app.services.notification_service import NotificationService
from app.services.poll_service import PollService
from app.services.realtime import events
from app.services.realtime.audience import emit_to_audience, resolve_audience
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import CommunityTarget

logger = structlog.get_logger(__name__)


class PostServiceBase:
    """@brief Constructor, event emission and notification helpers."""

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
        activity_repo: ActivityRepository | None = None,
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
        self._activity_repo = activity_repo

    def _enqueue_sassybot(self, post_id: uuid.UUID, content: str) -> None:
        """@brief Enqueue the Sassybot task (forced on @sassybot); never fails the request."""
        try:
            from app.tasks.ai_tasks import sassybot_comment_task

            sassybot_comment_task.apply_async(
                args=(str(post_id), str(self._community_id), wants_sassybot(content)),
                countdown=5,  # let the request transaction commit first
            )
        except Exception:
            logger.warning("sassybot_enqueue_failed", post_id=str(post_id))

    @property
    def _target(self) -> CommunityTarget:
        """@brief Nominal target for builders; real routing is per-user via audience."""
        return CommunityTarget(community_id=self._community_id)

    async def _emit_scoped(self, event: events.RealtimeEvent, post: Post) -> None:
        """@brief Emit a feed event only to users permitted to see ``post``."""
        if not self._event_bus:
            return
        audience = await resolve_audience(
            self._post_repo._session,
            self._community_id,
            visibility=post.visibility,
            subgroup_id=post.subgroup_id,
            author_id=post.author_id,
        )
        await emit_to_audience(self._event_bus, audience, event.type, event.payload)

    async def _publish_reaction_event(
        self,
        post: Post,
        post_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        emoji: str,
        count: int,
        action: str,
        user_id: uuid.UUID,
    ) -> None:
        """@brief Publish a reaction_toggled SSE event via the event bus."""
        await self._emit_scoped(
            events.reaction_toggled(
                self._target, post_id, target_type, target_id, emoji, count, action, user_id
            ),
            post,
        )

    async def _notify_mentions(self, content: str, actor: User, post_id: uuid.UUID) -> None:
        """@brief Notify @mentioned users in this community (never the actor)."""
        usernames = mentions.extract(content)
        if not usernames:
            return
        stmt = select(User).where(
            User.username.in_(usernames),
            User.community_id == self._community_id,
            User.deleted_at.is_(None),
        )
        result = await self._post_repo._session.execute(stmt)
        for mentioned in result.scalars().all():
            if mentioned.id == actor.id:
                continue
            await self._notification.notify(
                user_id=mentioned.id,
                type="mention",
                payload={
                    "post_id": str(post_id),
                    "actor_name": actor.display_name,
                    "message": _("%(user)s mentioned you in a post") % {"user": actor.display_name},
                    "link": f"/app/post/{post_id}",
                },
                actor_id=actor.id,
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
            "actor_name": user.display_name,
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
