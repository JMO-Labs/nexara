"""
@file newsletter_repo.py
@brief Newsletter queries. Every post/photo/recipe/event read goes through the
       shared viewer predicates, so nothing the viewer cannot open appears.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.media import Media
from app.models.newsletter import NewsletterOverride
from app.models.post import Comment, Post, PostMedia, Reaction
from app.models.recipe import Recipe
from app.models.user import User
from app.repositories.visibility_preds import (
    my_subgroup_ids,
    not_blocked,
    post_visible,
    recipe_visible,
)

TOP_POSTS = 8
PHOTOS = 12


class PostRow(NamedTuple):
    """@brief A visible post with its score and override."""

    post: Post
    author_name: str
    reactions: int
    comments: int
    action: str | None


class NewsletterRepository:
    """@brief Read helpers + override writes for one community."""

    def __init__(self, session: AsyncSession, community_id: uuid.UUID) -> None:
        self._s = session
        self._cid = community_id

    async def overrides(self, month: str) -> dict[uuid.UUID, str]:
        """@return post_id -> action for the month."""
        stmt = select(NewsletterOverride.post_id, NewsletterOverride.action).where(
            NewsletterOverride.community_id == self._cid, NewsletterOverride.month == month
        )
        return {pid: act for pid, act in (await self._s.execute(stmt)).all()}

    async def set_override(
        self, month: str, post_id: uuid.UUID, action: str | None, by: uuid.UUID
    ) -> None:
        """@brief Upsert (or clear when ``action`` is None) one override."""
        if action is None:
            await self._s.execute(
                delete(NewsletterOverride).where(
                    NewsletterOverride.community_id == self._cid,
                    NewsletterOverride.month == month,
                    NewsletterOverride.post_id == post_id,
                )
            )
            return
        stmt = insert(NewsletterOverride).values(
            community_id=self._cid, month=month, post_id=post_id, action=action, created_by=by
        )
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=["community_id", "month", "post_id"],
                set_={"action": action, "created_by": by},
            )
        )

    async def post_exists_visible(self, post_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
        """@brief Whether the viewer (an admin) may see the post being overridden."""
        stmt = select(Post.id).where(
            Post.id == post_id, post_visible(viewer_id, my_subgroup_ids(viewer_id), self._cid)
        )
        return (await self._s.execute(stmt)).first() is not None

    async def month_posts(
        self, viewer_id: uuid.UUID, start: datetime, end: datetime, month: str
    ) -> list[PostRow]:
        """@brief Posts of the month the viewer may open, scored; overrides attached."""
        rx = (
            select(func.count())
            .where(Reaction.target_type == "post", Reaction.target_id == Post.id)
            .scalar_subquery()
        )
        cm = select(func.count()).where(Comment.post_id == Post.id).scalar_subquery()
        ov = (
            select(NewsletterOverride.action)
            .where(
                NewsletterOverride.community_id == self._cid,
                NewsletterOverride.month == month,
                NewsletterOverride.post_id == Post.id,
            )
            .scalar_subquery()
        )
        stmt = (
            select(Post, User.display_name, rx, cm, ov)
            .join(User, User.id == Post.author_id)
            .where(
                post_visible(viewer_id, my_subgroup_ids(viewer_id), self._cid),
                Post.created_at >= start,
                Post.created_at < end,
                Post.is_nsfw.is_(False),
                Post.is_prompt_post.is_(False),
                Post.is_prompt_summary.is_(False),
            )
            .order_by((rx + cm).desc(), Post.created_at.desc())
            .limit(200)
        )
        return [
            PostRow(p, n, int(r), int(c), a)
            for p, n, r, c, a in (await self._s.execute(stmt)).all()
        ]

    async def post_media(
        self, post_ids: list[uuid.UUID]
    ) -> list[tuple[uuid.UUID, uuid.UUID, str | None]]:
        """@return (post_id, media_id, alt) for ready, non-NSFW images of the posts."""
        if not post_ids:
            return []
        stmt = (
            select(PostMedia.post_id, PostMedia.media_id, Media.alt_text)
            .join(Media, Media.id == PostMedia.media_id)
            .where(
                PostMedia.post_id.in_(post_ids),
                Media.community_id == self._cid,
                Media.content_type.like("image/%"),
                Media.status == "ready",
                Media.is_nsfw.is_(False),
            )
            .order_by(PostMedia.post_id, PostMedia.position)
        )
        return [(a, b, c) for a, b, c in (await self._s.execute(stmt)).all()]

    async def month_recipes(
        self, viewer_id: uuid.UUID, start: datetime, end: datetime, limit: int = 10
    ) -> list[tuple[Recipe, str]]:
        """@brief Recipes created in the month that the viewer may open."""
        stmt = (
            select(Recipe, User.display_name)
            .join(User, User.id == Recipe.author_id)
            .where(
                recipe_visible(viewer_id, my_subgroup_ids(viewer_id), self._cid),
                Recipe.created_at >= start,
                Recipe.created_at < end,
            )
            .order_by(Recipe.created_at)
            .limit(limit)
        )
        return [(r, n) for r, n in (await self._s.execute(stmt)).all()]

    async def month_events(
        self, viewer_id: uuid.UUID, start: datetime, end: datetime, limit: int = 20
    ) -> list[Event]:
        """@brief Events starting in the month that the viewer may see (no recurrences)."""
        in_group = Event.subgroup_id.in_(my_subgroup_ids(viewer_id))
        stmt = (
            select(Event)
            .where(
                Event.community_id == self._cid,
                Event.starts_at >= start,
                Event.starts_at < end,
                Event.source_removed.is_(False),
                or_(
                    and_(Event.visibility == "community", Event.subgroup_id.is_(None)),
                    and_(Event.visibility == "private", Event.author_id == viewer_id),
                    and_(Event.visibility == "subgroup", in_group),
                ),
                or_(Event.author_id == viewer_id, not_blocked(Event.author_id, viewer_id)),
            )
            .order_by(Event.starts_at)
            .limit(limit)
        )
        return list((await self._s.execute(stmt)).scalars())
