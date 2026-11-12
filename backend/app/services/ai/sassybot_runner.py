"""
@file sassybot_runner.py
@brief Orchestrates one Sassybot attempt: gating, generation, comment, event.
"""

from __future__ import annotations

import uuid

import structlog

from app.repositories.comment_repo import CommentRepository
from app.repositories.sassybot_repo import SassybotRepository
from app.services.ai.provider import AIBudgetExhaustedError, AIError
from app.services.ai.sassybot_service import MAX_THREAD_COMMENTS, SassybotService
from app.services.realtime import events
from app.services.realtime.audience import emit_to_audience, resolve_audience
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import CommunityTarget

logger = structlog.get_logger(__name__)


async def run_sassybot(
    post_id: uuid.UUID,
    community_id: uuid.UUID,
    *,
    force: bool,
    service: SassybotService,
    repo: SassybotRepository,
    comment_repo: CommentRepository,
    bot_user_id: uuid.UUID,
    event_bus: EventBus | None,
) -> bool:
    """
    @brief Run the Sassybot pipeline for a post.
    @param force Skip the probability/invoke-only gate (explicit @sassybot mention).
    @return True if a comment was created.
    """
    community = await repo.get_community(community_id)
    if community is None or not community.sassybot_enabled:
        return False
    if not force and not await service.should_trigger(post_id):
        return False
    if await service.count_thread_depth(post_id) >= MAX_THREAD_COMMENTS:
        return False
    try:
        text = await service.generate_comment(post_id, community_id)
    except AIBudgetExhaustedError:
        return False  # expected when budget is spent
    except AIError as exc:
        logger.warning("sassybot_ai_error", post_id=str(post_id), error=str(exc))
        return False
    if not text:
        return False

    comment = await comment_repo.create_comment(
        post_id=post_id, author_id=bot_user_id, content=text, community_id=community_id
    )
    found = await repo.get_post_and_author(post_id, community_id)
    if event_bus is not None and found is not None:
        post = found[0]
        payload = {
            "id": str(comment.id),
            "content": comment.content,
            "author": {
                "id": str(bot_user_id),
                "username": "sassybot",
                "display_name": "Sassybot",
                "avatar_url": None,
            },
            "parent_id": None,
            "created_at": comment.created_at.isoformat(),
            "replies": [],
            "reactions": [],
        }
        event = events.comment_created(
            CommunityTarget(community_id=community_id), post_id, payload, bot_user_id
        )
        audience = await resolve_audience(
            repo._session,
            community_id,
            visibility=post.visibility,
            subgroup_id=post.subgroup_id,
            author_id=post.author_id,
        )
        await emit_to_audience(event_bus, audience, event.type, event.payload)
    return True
