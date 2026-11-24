"""
@file events.py
@brief Decide which plugins receive a post/comment/mention webhook and enqueue delivery.

A plugin only ever gets content its bot account could see: community posts, or
subgroup posts when the bot is a member. Private and NSFW posts, bot-authored
content and authors who blocked (or are blocked by) the bot are never sent.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Comment, Post
from app.models.user import User
from app.plugins.manifest import PluginManifest
from app.repositories.plugin_repo import PluginRepository
from app.services import mentions
from app.services.plugin_settings import prefs_with_defaults
from app.services.realtime.audience import resolve_audience

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
    @brief Enqueue signed webhooks for a new post or comment; never raises.
    @param post The post (the parent post for a comment).
    @param comment The new comment, or None for a new post.
    @param author Author of the post/comment.
    @param parent_author_id Author of the replied-to comment, if any.
    """
    try:
        await _dispatch(session, community_id, post, comment, author, parent_author_id)
    except Exception:
        logger.warning("plugin_dispatch_failed", post_id=str(post.id))


async def _dispatch(
    session: AsyncSession,
    community_id: uuid.UUID,
    post: Post,
    comment: Comment | None,
    author: User,
    parent_author_id: uuid.UUID | None,
) -> None:
    if author.is_bot or post.is_nsfw or post.visibility == "private":
        return
    from app.tasks.plugin_tasks import deliver_plugin_event

    kind = "comment" if comment else "post"
    content = comment.content if comment else post.content
    mentioned = {u.lower() for u in mentions.extract(content)}
    events = [f"{kind}.created"]
    repo = PluginRepository(session)
    audience: set[uuid.UUID] | None = None
    post_data: dict[str, Any] | None = None
    for event in events + ["mention"]:
        for inst, pc in await repo.list_enabled_for_event(community_id, event):
            m = PluginManifest.model_validate(inst.manifest)
            if (
                f"{kind}s:read" not in inst.granted_scopes
                or not inst.endpoint_url
                or not pc.webhook_secret
                or pc.bot_user_id is None
                or (event == "mention" and m.bot_username.lower() not in mentioned)
            ):
                continue
            if audience is None:
                audience = set(
                    await resolve_audience(
                        session,
                        community_id,
                        visibility=post.visibility,
                        subgroup_id=post.subgroup_id,
                        author_id=post.author_id,
                    )
                )
            if pc.bot_user_id not in audience:
                continue
            if post_data is None:
                post_data = await _post_dict(repo, post)
            prefs = prefs_with_defaults(
                m, await repo.get_user_pref(inst.id, author.id, community_id)
            )
            delivery_id = str(uuid.uuid4())
            data: dict[str, Any] = {
                "post": post_data,
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
                    "event": event,
                    "community_id": str(community_id),
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "data": data,
                }
            )
            deliver_plugin_event.delay(inst.endpoint_url, pc.webhook_secret, body, delivery_id)
