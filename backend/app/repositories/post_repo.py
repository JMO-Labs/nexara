"""
@file post_repo.py
@brief Repository for posts.

Provides cursor-paginated feed queries with author, media, reactions,
and comment counts. All queries apply soft-delete filtering and
community_id scoping.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select

from app.models.poll import Poll, PollOption, PollVote
from app.models.post import Comment, Post, PostMedia, Reaction
from app.models.subgroup import Subgroup
from app.models.user import User
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)

DEFAULT_PAGE_SIZE = 20
"""@brief Default number of items per page."""

MAX_PAGE_SIZE = 50
"""@brief Maximum items per page."""


class PostRepository(BaseRepository[Post]):
    """
    @brief Async repository for post CRUD with feed pagination.

    @param session Async SQLAlchemy session.
    """

    model = Post

    async def list_feed(
        self,
        community_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        subgroup_id: uuid.UUID | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief Fetch paginated feed posts with author, media, reactions, and comment count.

        @param community_id Community scope.
        @param viewer_id Current user UUID for block filter and reaction state.
        @param cursor Opaque cursor (ISO timestamp of last seen post).
        @param limit Number of posts to return.
        @param subgroup_id Optional subgroup ID to filter posts.
        @return Tuple of (enriched post dicts, next_cursor).
        """
        limit = min(limit, MAX_PAGE_SIZE)

        stmt = (
            self._base_query()
            .where(Post.community_id == community_id)
            .order_by(Post.created_at.desc())
        )

        if cursor:
            from datetime import datetime

            try:
                cursor_ts = datetime.fromisoformat(cursor)
                stmt = stmt.where(Post.created_at < cursor_ts)
            except (ValueError, TypeError):
                pass

        if subgroup_id is not None:
            stmt = stmt.where(Post.subgroup_id == subgroup_id)

        if viewer_id:
            stmt = self.apply_block_filter(stmt, viewer_id)

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].created_at.isoformat()

        if not rows:
            return [], None

        post_ids = [p.id for p in rows]
        posts_data = await self._enrich_posts(post_ids, viewer_id)

        ordered = []
        for post in rows:
            data = posts_data.get(post.id)
            if data:
                ordered.append(data)

        return ordered, next_cursor

    async def count_new_since(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        since: Any,
    ) -> int:
        """
        @brief Count posts visible to viewer created after ``since``.

        @param community_id Community scope.
        @param viewer_id Viewer UUID for block filter.
        @param since Datetime cutoff (posts created after this are counted).
        @return Integer count of new posts.
        """
        from datetime import datetime as dt

        stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.community_id == community_id)
            .where(Post.deleted_at.is_(None))
        )
        if isinstance(since, dt):
            stmt = stmt.where(Post.created_at > since)
        stmt = self.apply_block_filter(stmt, viewer_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_post_detail(
        self,
        post_id: uuid.UUID,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
    ) -> dict[str, Any] | None:
        """
        @brief Fetch a single post with full enrichment.

        @param post_id Post UUID.
        @param community_id Community scope.
        @param viewer_id Current user for reaction state.
        @return Enriched post dict or None.
        """
        stmt = self._base_query().where(Post.id == post_id, Post.community_id == community_id)
        result = await self._session.execute(stmt)
        post = result.scalar_one_or_none()
        if not post:
            return None

        enriched = await self._enrich_posts([post_id], viewer_id)
        return enriched.get(post_id)

    async def create_post(
        self,
        author_id: uuid.UUID,
        content: str,
        community_id: uuid.UUID,
        reply_to_prompt_id: uuid.UUID | None = None,
        subgroup_id: uuid.UUID | None = None,
    ) -> Post:
        """
        @brief Insert a new post row.

        @param author_id Author UUID.
        @param content Markdown content.
        @param community_id Community scope.
        @param reply_to_prompt_id Optional prompt post UUID for reply tracking.
        @param subgroup_id Optional subgroup UUID to scope the post.
        @return The created Post ORM instance.
        """
        post = Post(
            author_id=author_id,
            content=content,
            community_id=community_id,
            reply_to_prompt_id=reply_to_prompt_id,
            subgroup_id=subgroup_id,
        )
        return await self.create(post)

    async def update_content(
        self,
        post: Post,
        content: str,
    ) -> Post:
        """
        @brief Update a post's text content.

        @param post The Post ORM instance.
        @param content New markdown content.
        @return The updated Post ORM instance.
        """
        post.content = content
        await self._session.flush()
        await self._session.refresh(post)
        return post

    async def soft_delete_post(
        self,
        post_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> bool:
        """
        @brief Soft-delete a post by ID.

        @param post_id Post UUID.
        @param community_id Community scope.
        @return True if a post was deleted, False if not found.
        """
        post = await self.get_by_id(post_id, community_id=community_id)
        if not post:
            return False
        await self.soft_delete(post)
        return True

    async def list_replies_for_prompt(
        self,
        prompt_id: uuid.UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        @brief Fetch posts that are replies to a prompt, with media IDs.

        @param prompt_id Prompt UUID to filter replies.
        @param limit Maximum number of posts to return.
        @return List of dicts with post data and media_ids list.
        """
        from app.models.media import Media

        stmt = (
            self._base_query()
            .where(Post.reply_to_prompt_id == prompt_id)
            .order_by(Post.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        posts = list(result.scalars().all())

        if not posts:
            return []

        post_ids = [p.id for p in posts]

        media_stmt = (
            select(PostMedia.post_id, Media.id)
            .join(Media, PostMedia.media_id == Media.id)
            .where(PostMedia.post_id.in_(post_ids))
            .order_by(PostMedia.position)
        )
        media_result = await self._session.execute(media_stmt)
        media_map: dict[uuid.UUID, list[uuid.UUID]] = {}
        for pm_post_id, media_id in media_result.all():
            media_map.setdefault(pm_post_id, []).append(media_id)

        return [
            {
                "id": p.id,
                "media_ids": media_map.get(p.id, []),
            }
            for p in posts
        ]

    async def _enrich_posts(
        self,
        post_ids: list[uuid.UUID],
        viewer_id: uuid.UUID | None,
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        @brief Batch-load authors, media, reactions, and comment counts for posts.

        @param post_ids List of post UUIDs.
        @param viewer_id Current user for `reacted_by_me` flag.
        @return Dict mapping post_id -> enriched dict.
        """
        posts_stmt = (
            select(Post, User).join(User, Post.author_id == User.id).where(Post.id.in_(post_ids))
        )
        posts_result = await self._session.execute(posts_stmt)
        post_rows = posts_result.all()

        # Load subgroup names for posts that belong to a subgroup
        subgroup_ids = {p.subgroup_id for p, _ in post_rows if p.subgroup_id is not None}
        subgroup_name_map: dict[uuid.UUID, str] = {}
        if subgroup_ids:
            sg_stmt = select(Subgroup.id, Subgroup.name).where(Subgroup.id.in_(subgroup_ids))
            sg_result = await self._session.execute(sg_stmt)
            subgroup_name_map = {sg_id: sg_name for sg_id, sg_name in sg_result.all()}

        from app.models.media import Media

        media_stmt = (
            select(PostMedia.post_id, Media)
            .join(Media, PostMedia.media_id == Media.id)
            .where(PostMedia.post_id.in_(post_ids))
            .order_by(PostMedia.position)
        )
        media_result = await self._session.execute(media_stmt)
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
        reaction_result = await self._session.execute(reaction_stmt)
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
            my_result = await self._session.execute(my_reactions_stmt)
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
        comment_result = await self._session.execute(comment_stmt)
        comment_map = {pid: cnt for pid, cnt in comment_result.all()}

        # Polls attached to posts
        poll_stmt = select(Poll).where(Poll.post_id.in_(post_ids))
        poll_result = await self._session.execute(poll_stmt)
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
        # voters per (poll_id, option_id) for non-anonymous polls
        poll_voters: dict[tuple[uuid.UUID, uuid.UUID], list[dict[str, Any]]] = {}
        if poll_ids:
            opt_stmt = (
                select(PollOption)
                .where(PollOption.poll_id.in_(poll_ids))
                .order_by(PollOption.position)
            )
            opt_result = await self._session.execute(opt_stmt)
            for opt in opt_result.scalars().all():
                poll_options_map.setdefault(opt.poll_id, []).append(opt)

            vote_stmt = (
                select(PollVote.poll_id, PollVote.option_id, func.count().label("cnt"))
                .where(PollVote.poll_id.in_(poll_ids))
                .group_by(PollVote.poll_id, PollVote.option_id)
            )
            vote_result = await self._session.execute(vote_stmt)
            for pid, oid, cnt in vote_result.all():
                poll_vote_counts.setdefault(pid, {})[oid] = cnt

            if viewer_id:
                uv_stmt = select(PollVote.poll_id, PollVote.option_id).where(
                    PollVote.poll_id.in_(poll_ids), PollVote.user_id == viewer_id
                )
                uv_result = await self._session.execute(uv_stmt)
                for pid, oid in uv_result.all():
                    poll_user_votes.setdefault(pid, []).append(str(oid))

            # Load voters for non-anonymous polls
            non_anon_poll_ids = [p.id for p in polls if not p.is_anonymous]
            if non_anon_poll_ids:
                voters_stmt = (
                    select(PollVote.poll_id, PollVote.option_id, User)
                    .join(User, PollVote.user_id == User.id)
                    .where(PollVote.poll_id.in_(non_anon_poll_ids))
                )
                voters_result = await self._session.execute(voters_stmt)
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

            # Apply result_visibility: hide counts when viewer shouldn't see them
            show_results = False
            if poll.result_visibility == "always":
                show_results = True
            elif poll.result_visibility == "after_vote" and user_vote:
                show_results = True
            elif poll.result_visibility == "after_expiry":
                from datetime import UTC
                from datetime import datetime as dt

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
