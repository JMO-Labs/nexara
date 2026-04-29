"""
@file post_enrichment.py
@brief Batch enrichment helpers for post feed queries.

Provides _enrich_posts: loads authors, media, reactions, comment counts,
and polls for a list of post IDs in a single batch of async queries.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poll import Poll, PollOption, PollVote
from app.models.post import Comment, PostMedia, Reaction
from app.models.subgroup import Subgroup
from app.models.user import User


async def enrich_posts(
    session: AsyncSession,
    post_ids: list[uuid.UUID],
    viewer_id: uuid.UUID | None,
) -> dict[uuid.UUID, dict[str, Any]]:
    """
    @brief Batch-load authors, media, reactions, and comment counts for posts.

    @param session Async SQLAlchemy session.
    @param post_ids List of post UUIDs.
    @param viewer_id Current user for ``reacted_by_me`` flag.
    @return Dict mapping post_id -> enriched dict.
    """
    from app.models.post import Post

    posts_stmt = (
        select(Post, User).join(User, Post.author_id == User.id).where(Post.id.in_(post_ids))
    )
    posts_result = await session.execute(posts_stmt)
    post_rows = posts_result.all()

    subgroup_ids = {p.subgroup_id for p, _ in post_rows if p.subgroup_id is not None}
    subgroup_name_map: dict[uuid.UUID, str] = {}
    if subgroup_ids:
        sg_stmt = select(Subgroup.id, Subgroup.name).where(Subgroup.id.in_(subgroup_ids))
        sg_result = await session.execute(sg_stmt)
        subgroup_name_map = {sg_id: sg_name for sg_id, sg_name in sg_result.all()}

    from app.models.media import Media

    media_stmt = (
        select(PostMedia.post_id, Media)
        .join(Media, PostMedia.media_id == Media.id)
        .where(PostMedia.post_id.in_(post_ids))
        .order_by(PostMedia.position)
    )
    media_result = await session.execute(media_stmt)
    media_map: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for pm_post_id, media in media_result.all():
        media_map.setdefault(pm_post_id, []).append(
            {
                "id": str(media.id),
                "url": f"/api/v1/media/{media.id}/file",
                "thumbnail_url": f"/api/v1/media/{media.id}/thumbnail"
                if media.thumbnail_key
                else None,
                "mime_type": media.content_type,
                "width": media.width,
                "height": media.height,
            }
        )

    reaction_stmt = (
        select(
            Reaction.target_id,
            Reaction.emoji,
            func.count().label("cnt"),
        )
        .where(Reaction.target_type == "post", Reaction.target_id.in_(post_ids))
        .group_by(Reaction.target_id, Reaction.emoji)
    )
    reaction_result = await session.execute(reaction_stmt)
    reaction_map: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for target_id, emoji, cnt in reaction_result.all():
        reaction_map.setdefault(target_id, []).append(
            {
                "emoji": emoji,
                "count": cnt,
                "reacted_by_me": False,
            }
        )

    if viewer_id:
        my_reactions_stmt = select(Reaction.target_id, Reaction.emoji).where(
            Reaction.target_type == "post",
            Reaction.target_id.in_(post_ids),
            Reaction.user_id == viewer_id,
        )
        my_result = await session.execute(my_reactions_stmt)
        my_set = {(tid, em) for tid, em in my_result.all()}
        for pid, reactions in reaction_map.items():
            for r in reactions:
                if (pid, r["emoji"]) in my_set:
                    r["reacted_by_me"] = True

    comment_stmt = (
        select(Comment.post_id, func.count().label("cnt"))
        .where(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
    )
    comment_result = await session.execute(comment_stmt)
    comment_map = {pid: cnt for pid, cnt in comment_result.all()}

    poll_stmt = select(Poll).where(Poll.post_id.in_(post_ids))
    poll_result = await session.execute(poll_stmt)
    polls = list(poll_result.scalars().all())
    poll_by_post: dict[uuid.UUID, Poll] = {}
    poll_ids: list[uuid.UUID] = []
    for p in polls:
        if p.post_id:
            poll_by_post[p.post_id] = p
            poll_ids.append(p.id)

    poll_options_map: dict[uuid.UUID, list[PollOption]] = {}
    poll_vote_counts: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    poll_user_votes: dict[uuid.UUID, list[str]] = {}
    poll_voters: dict[tuple[uuid.UUID, uuid.UUID], list[dict[str, Any]]] = {}
    if poll_ids:
        opt_stmt = (
            select(PollOption).where(PollOption.poll_id.in_(poll_ids)).order_by(PollOption.position)
        )
        opt_result = await session.execute(opt_stmt)
        for opt in opt_result.scalars().all():
            poll_options_map.setdefault(opt.poll_id, []).append(opt)

        vote_stmt = (
            select(PollVote.poll_id, PollVote.option_id, func.count().label("cnt"))
            .where(PollVote.poll_id.in_(poll_ids))
            .group_by(PollVote.poll_id, PollVote.option_id)
        )
        vote_result = await session.execute(vote_stmt)
        for pid, oid, cnt in vote_result.all():
            poll_vote_counts.setdefault(pid, {})[oid] = cnt

        if viewer_id:
            uv_stmt = select(PollVote.poll_id, PollVote.option_id).where(
                PollVote.poll_id.in_(poll_ids), PollVote.user_id == viewer_id
            )
            uv_result = await session.execute(uv_stmt)
            for pid, oid in uv_result.all():
                poll_user_votes.setdefault(pid, []).append(str(oid))

        non_anon_poll_ids = [p.id for p in polls if not p.is_anonymous]
        if non_anon_poll_ids:
            voters_stmt = (
                select(PollVote.poll_id, PollVote.option_id, User)
                .join(User, PollVote.user_id == User.id)
                .where(PollVote.poll_id.in_(non_anon_poll_ids))
            )
            voters_result = await session.execute(voters_stmt)
            for pid, oid, voter in voters_result.all():
                poll_voters.setdefault((pid, oid), []).append(
                    {
                        "id": str(voter.id),
                        "display_name": voter.display_name,
                        "avatar_url": voter.avatar_url,
                    }
                )

    poll_map: dict[uuid.UUID, dict[str, Any]] = {}
    for post_id_key, poll in poll_by_post.items():
        opts = poll_options_map.get(poll.id, [])
        counts = poll_vote_counts.get(poll.id, {})
        total = sum(counts.values())
        user_vote = poll_user_votes.get(poll.id)

        show_results = False
        if poll.result_visibility == "always":
            show_results = True
        elif poll.result_visibility == "after_vote" and user_vote:
            show_results = True
        elif poll.result_visibility == "after_expiry":
            is_expired = poll.expires_at is not None and poll.expires_at < dt.now(UTC)
            show_results = poll.closed or is_expired

        visible_counts = counts if show_results else {}
        visible_total = total if show_results else 0
        include_voters = show_results and not poll.is_anonymous

        poll_map[post_id_key] = {
            "id": str(poll.id),
            "post_id": str(poll.post_id) if poll.post_id else None,
            "poll_type": poll.poll_type,
            "question": poll.question,
            "options": [
                {
                    "id": str(o.id),
                    "label": o.label,
                    "image_media_id": str(o.image_media_id) if o.image_media_id else None,
                    "position": o.position,
                    "vote_count": visible_counts.get(o.id, 0),
                    "voters": poll_voters.get((poll.id, o.id), []) if include_voters else [],
                }
                for o in opts
            ],
            "is_anonymous": poll.is_anonymous,
            "result_visibility": poll.result_visibility,
            "expires_at": poll.expires_at.isoformat() if poll.expires_at else None,
            "closed": poll.closed,
            "total_votes": visible_total,
            "user_vote": user_vote if show_results else None,
            "created_at": poll.created_at.isoformat(),
        }

    enriched: dict[uuid.UUID, dict[str, Any]] = {}
    for post, author in post_rows:
        enriched[post.id] = {
            "id": str(post.id),
            "content": post.content,
            "author": {
                "id": str(author.id),
                "username": author.username,
                "display_name": author.display_name,
                "avatar_url": author.avatar_url,
            },
            "media": media_map.get(post.id, []),
            "poll": poll_map.get(post.id),
            "reactions": reaction_map.get(post.id, []),
            "comment_count": comment_map.get(post.id, 0),
            "subgroup_id": str(post.subgroup_id) if post.subgroup_id else None,
            "subgroup_name": (
                subgroup_name_map.get(post.subgroup_id) if post.subgroup_id else None
            ),
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
        }
    return enriched
