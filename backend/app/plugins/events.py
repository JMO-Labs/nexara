"""
@file events.py
@brief Decide which plugins receive a post/comment/mention webhook and enqueue delivery.

A plugin only ever gets content its bot account could read over REST
(``PostRepository.is_visible``: group membership, private, blocks, hidden
answers, NSFW). Bot-authored content, NSFW media and comments whose author is
in a block relation with the bot are never sent.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.post import Comment, Post
from app.models.user import User
from app.plugins.manifest import PluginManifest
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.plugin_repo import PluginRepository
from app.repositories.post_repo import PostRepository
from app.services import mentions
from app.services.plugin_settings import prefs_with_defaults

logger = structlog.get_logger(__name__)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def _post_dict(repo: PluginRepository, post: Post) -> dict[str, Any]:
    media = await repo.list_post_media(post.id)
    return {
        "id": str(post.id),
        "content": post.content,
        "visibility": post.visibility,
        "subgroup_id": str(post.subgroup_id) if post.subgroup_id else None,
        "author_id": str(post.author_id),
        "created_at": _iso(post.created_at),
        "media": [
            {"id": str(mid), "mime": mime, "url": f"/api/v1/media/{mid}/file"}
            for mid, mime in media
        ],
    }


def _comment_dict(comment: Comment, parent_author_id: uuid.UUID | None) -> dict[str, Any]:
    return {
        "id": str(comment.id),
        "content": comment.content,
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
        "parent_author_id": str(parent_author_id) if parent_author_id else None,
        "created_at": _iso(comment.created_at),
    }


def schedule_plugin_dispatch(
    session: AsyncSession, community_id: uuid.UUID, post_id: uuid.UUID, comment_id: uuid.UUID | None
) -> None:
    """
    @brief Enqueue plugin dispatch only AFTER the request transaction commits.

    Registers a SQLAlchemy ``after_commit`` hook on the session (once); a rollback
    discards pending jobs, so a failed request never announces content. Enqueue
    errors are logged and never reach the request.
    @param post_id Post that was created (or commented on).
    @param comment_id New comment, or None for a new post.
    """
    try:
        _register(session, community_id, post_id, comment_id)
    except Exception:
        logger.warning("plugin_dispatch_schedule_failed", exc_info=True)


def _register(
    session: AsyncSession, community_id: uuid.UUID, post_id: uuid.UUID, comment_id: uuid.UUID | None
) -> None:
    sync: Session = session.sync_session
    pending: list[tuple[str, ...]] = sync.info.setdefault("plugin_dispatch", [])
    pending.append((str(community_id), str(post_id), str(comment_id) if comment_id else ""))
    if sync.info.get("plugin_dispatch_hooked"):
        return
    sync.info["plugin_dispatch_hooked"] = True

    def _flush(_: Session) -> None:
        jobs, sync.info["plugin_dispatch"] = list(sync.info.get("plugin_dispatch", [])), []
        from app.tasks.plugin_tasks import dispatch_plugin_event_task

        for job in jobs:
            try:
                dispatch_plugin_event_task.apply_async(args=job, countdown=1)
            except Exception:
                logger.warning("plugin_dispatch_enqueue_failed", exc_info=True)

    def _drop(_: Session) -> None:
        sync.info["plugin_dispatch"] = []

    event.listen(sync, "after_commit", _flush)
    event.listen(sync, "after_rollback", _drop)


async def dispatch_plugin_event(
    session: AsyncSession,
    community_id: uuid.UUID,
    *,
    post: Post,
    comment: Comment | None,
    author: User,
    parent_author_id: uuid.UUID | None = None,
) -> None:
    """
    @brief Select receiving plugins and enqueue signed webhooks (worker side); never raises.
    @param post The post (the parent post for a comment).
    @param comment The new comment, or None for a new post.
    @param author Author of the post/comment.
    @param parent_author_id Author of the replied-to comment, if any.
    """
    try:
        await _dispatch(session, community_id, post, comment, author, parent_author_id)
    except Exception:
        logger.warning("plugin_dispatch_failed", post_id=str(post.id), exc_info=True)


async def _bot_can_see(
    session: AsyncSession,
    community_id: uuid.UUID,
    post: Post,
    author: User,
    comment: Comment | None,
    bot_id: uuid.UUID,
) -> bool:
    """@brief Same rule as REST reads, plus no block between commenter and bot."""
    if not await PostRepository(session).is_visible(post.id, bot_id, community_id):
        return False
    return not (
        comment is not None
        and await ModerationRepository(session).is_blocked_either(author.id, bot_id)
    )


async def _dispatch(
    session: AsyncSession,
    community_id: uuid.UUID,
    post: Post,
    comment: Comment | None,
    author: User,
    parent_author_id: uuid.UUID | None,
) -> None:
    if author.is_bot or post.is_nsfw or post.visibility == "private":
        return  # cheap early exits; _bot_can_see is the real gate
    from app.tasks.plugin_tasks import deliver_plugin_event

    kind = "comment" if comment else "post"
    content = comment.content if comment else post.content
    mentioned = {u.lower() for u in mentions.extract(content)}
    repo = PluginRepository(session)
    seen: dict[uuid.UUID, bool] = {}
    post_data: dict[str, Any] | None = None
    for ev in (f"{kind}.created", "mention"):
        for inst, pc in await repo.list_enabled_for_event(community_id, ev):
            m = PluginManifest.model_validate(inst.manifest)
            if (
                f"{kind}s:read" not in inst.granted_scopes
                or not inst.endpoint_url
                or not pc.webhook_secret
                or pc.bot_user_id is None
            ):
                continue
            if ev == "mention":
                name = (await repo.get_usernames([pc.bot_user_id])).get(pc.bot_user_id, "")
                if name.lower() not in mentioned:
                    continue
            bot = pc.bot_user_id
            if bot not in seen:
                seen[bot] = await _bot_can_see(session, community_id, post, author, comment, bot)
            if not seen[bot]:
                continue
            can_post = "posts:read" in inst.granted_scopes
            if post_data is None:
                post_data = await _post_dict(repo, post)
            prefs = prefs_with_defaults(
                m, await repo.get_user_pref(inst.id, author.id, community_id)
            )
            delivery_id = str(uuid.uuid4())
            data: dict[str, Any] = {
                "post": post_data if can_post else {"id": str(post.id)},
                "author": {
                    "id": str(author.id),
                    "username": author.username,
                    "display_name": author.display_name,
                },
                "author_prefs": prefs,
                "flags": (post.plugin_flags or {}).get(inst.plugin_id, {}),
            }
            if comment:
                data["comment"] = _comment_dict(comment, parent_author_id)
            body = json.dumps(
                {
                    "delivery_id": delivery_id,
                    "event": ev,
                    "community_id": str(community_id),
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "data": data,
                }
            )
            deliver_plugin_event.delay(inst.endpoint_url, pc.webhook_secret, body, delivery_id)
