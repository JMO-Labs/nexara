"""
@file home_needs_repo.py
@brief HomeNeedsRepository: read-only queries for the "needs you" chips.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.event import Event, EventAttendance
from app.models.list import List, ListItem, ListMember
from app.models.moderation import UserBlock
from app.models.poll import Poll, PollVote
from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.repositories.base import BaseRepository
from app.repositories.visibility_preds import nsfw_allowed, viewer_is_adult


def _post_visible(subgroup_ids: list[uuid.UUID]) -> Any:
    """@brief Post is community-wide (no subgroup) or in one of the viewer's subgroups."""
    in_group = Post.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False)
    return and_(
        Post.deleted_at.is_(None),
        Post.visibility != "private",
        or_(Post.subgroup_id.is_(None), in_group),
    )


def _not_blocked(author_col: Any, viewer_id: uuid.UUID) -> Any:
    """@brief Author is not in a block relation with the viewer."""
    by_viewer = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
    of_viewer = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
    return and_(author_col.notin_(by_viewer), author_col.notin_(of_viewer))


class HomeNeedsRepository(BaseRepository[Event]):
    """@brief Queries for pending RSVPs, open polls, prompts and due list items."""

    model = Event

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async DB session."""
        super().__init__(session)

    async def pending_rsvps(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID],
        now: datetime,
        days: int = 14,
        limit: int = 5,
    ) -> list[Event]:
        """
        @brief Visible upcoming events the viewer neither authored nor answered.
        @return Events ascending by start time.
        """
        in_group = Event.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False)
        answered = exists().where(
            EventAttendance.event_id == Event.id, EventAttendance.user_id == viewer_id
        )
        stmt = select(Event).where(
            Event.community_id == community_id,
            Event.starts_at >= now,
            Event.starts_at <= now + timedelta(days=days),
            Event.author_id != viewer_id,
            or_(
                Event.visibility == "community",
                and_(Event.visibility == "subgroup", in_group),
            ),
            ~answered,
            _not_blocked(Event.author_id, viewer_id),
        )
        stmt = stmt.order_by(Event.starts_at.asc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())

    async def open_polls(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID],
        now: datetime,
        limit: int = 5,
    ) -> list[Poll]:
        """@brief Recent open polls (last 7 days) the viewer has not voted on, newest first."""
        voted = exists().where(PollVote.poll_id == Poll.id, PollVote.user_id == viewer_id)
        stmt = (
            select(Poll)
            .join(Post, Post.id == Poll.post_id)
            .where(
                Poll.community_id == community_id,
                Post.community_id == community_id,
                Poll.deleted_at.is_(None),
                Poll.closed.is_(False),
                or_(Poll.expires_at.is_(None), Poll.expires_at > now),
                Post.created_at >= now - timedelta(days=7),
                Post.author_id != viewer_id,
                _post_visible(subgroup_ids),
                _not_blocked(Post.author_id, viewer_id),
                nsfw_allowed(viewer_is_adult(viewer_id)),
                ~voted,
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def unanswered_prompt(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID],
        now: datetime,
    ) -> tuple[uuid.UUID, uuid.UUID, str] | None:
        """
        @brief Newest active prompt, visible to the viewer, they have not replied to.
        @param subgroup_ids Viewer's subgroups; subgroup-scoped prompts outside them are hidden.
        @return (prompt_post_id, post_id, prompt title) or None.
        """
        prompt_post = aliased(Post)
        sg_ok = Prompt.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False)
        post_sg_ok = prompt_post.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False)
        answered = exists().where(
            Post.reply_to_prompt_id == PromptPost.id,
            Post.author_id == viewer_id,
            Post.deleted_at.is_(None),
        )
        stmt = (
            select(PromptPost.id, PromptPost.post_id, Prompt.title)
            .join(Prompt, Prompt.id == PromptPost.prompt_id)
            .join(prompt_post, prompt_post.id == PromptPost.post_id)
            .where(
                PromptPost.community_id == community_id,
                or_(Prompt.subgroup_id.is_(None), sg_ok),
                or_(prompt_post.subgroup_id.is_(None), post_sg_ok),
                prompt_post.deleted_at.is_(None),
                _not_blocked(prompt_post.author_id, viewer_id),
                PromptPost.is_finalised.is_(False),
                PromptPost.expires_at > now,
                ~answered,
            )
            .order_by(PromptPost.fired_at.desc(), PromptPost.expires_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1], row[2]) if row else None

    async def due_list_items(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID],
        now: datetime,
        days: int = 7,
    ) -> tuple[int, uuid.UUID | None, str | None]:
        """
        @brief Count open items due within ``days`` in lists the viewer can see.
        @return (count, list_id of soonest item, its title); (0, None, None) when none.
        """
        in_group = List.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False)
        member_of = exists().where(ListMember.list_id == List.id, ListMember.user_id == viewer_id)
        visible = or_(
            List.visibility == "community",
            and_(List.visibility == "private", List.owner_id == viewer_id),
            and_(List.visibility == "subgroup", in_group),
            and_(List.visibility == "members", or_(List.owner_id == viewer_id, member_of)),
        )
        base = (
            select(ListItem.list_id, List.title, ListItem.due_at)
            .join(List, List.id == ListItem.list_id)
            .where(
                List.community_id == community_id,
                List.status == "active",
                List.deleted_at.is_(None),
                ListItem.deleted_at.is_(None),
                ListItem.completed.is_(False),
                ListItem.due_at >= now,
                ListItem.due_at <= now + timedelta(days=days),
                visible,
                _not_blocked(List.owner_id, viewer_id),
            )
        )
        sub = base.subquery()
        count = (await self._session.execute(select(func.count()).select_from(sub))).scalar_one()
        if not count:
            return (0, None, None)
        top = (await self._session.execute(base.order_by(ListItem.due_at.asc()).limit(1))).one()
        return (int(count), top[0], top[1])
