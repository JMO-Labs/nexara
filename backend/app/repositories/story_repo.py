"""
@file story_repo.py
@brief Data access for story requests: party checks, state transitions,
       daily reminder/expiry claims and the viewer-scoped Stories tab.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.post import Post, PostMedia
from app.models.story_request import EXPIRY, REMIND_AFTER, StoryRequest
from app.models.user import User
from app.repositories.post_enrichment import enrich_posts
from app.repositories.visibility_preds import my_subgroup_ids, post_visible

SR = StoryRequest
LIVE = ("open", "declined")
"""@brief Statuses that still count as pending (``declined`` is hidden from the asker)."""


class StoryRepository:
    """@brief Async repository for ``story_requests``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def usable_pair(
        self, user_id: uuid.UUID, other_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@return True if ``user_id`` is a live member not blocked with ``other_id``."""
        ok = select(User.id).where(
            User.id == user_id,
            User.community_id == community_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.memorialized_at.is_(None),
        )
        blocked = exists().where(
            or_(
                (UserBlock.blocker_id == user_id) & (UserBlock.blocked_id == other_id),
                (UserBlock.blocker_id == other_id) & (UserBlock.blocked_id == user_id),
            )
        )
        stmt = select(exists(ok).where(~blocked))
        return bool((await self._session.execute(stmt)).scalar())

    async def blocked_between(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        """@return True when either user blocks the other."""
        stmt = select(
            exists().where(
                or_(
                    (UserBlock.blocker_id == a) & (UserBlock.blocked_id == b),
                    (UserBlock.blocker_id == b) & (UserBlock.blocked_id == a),
                )
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@return display names by user id."""
        rows = await self._session.execute(
            select(User.id, User.display_name).where(User.id.in_(ids))
        )
        return {i: n for i, n in rows.all()}

    async def count_pending(self, asker_id: uuid.UUID, teller_id: uuid.UUID, now: datetime) -> int:
        """@return Unexpired open/declined asks from asker to teller."""
        stmt = select(func.count()).where(
            SR.asker_id == asker_id,
            SR.teller_id == teller_id,
            SR.status.in_(LIVE),
            SR.expires_at > now,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def create(
        self,
        community_id: uuid.UUID,
        asker_id: uuid.UUID,
        teller_id: uuid.UUID,
        question: str,
        now: datetime,
    ) -> StoryRequest:
        """@brief Insert an open request expiring in 30 days."""
        row = SR(
            community_id=community_id,
            asker_id=asker_id,
            teller_id=teller_id,
            question=question,
            status="open",
            created_at=now,
            expires_at=now + EXPIRY,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, request_id: uuid.UUID, community_id: uuid.UUID) -> StoryRequest | None:
        """@return The request or None."""
        stmt = select(SR).where(SR.id == request_id, SR.community_id == community_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for(
        self, user_id: uuid.UUID, community_id: uuid.UUID, now: datetime
    ) -> list[StoryRequest]:
        """@return Requests the user asked, or open unexpired ones awaiting them, newest first."""
        stmt = (
            select(SR)
            .where(
                SR.community_id == community_id,
                or_(
                    SR.asker_id == user_id,
                    (SR.teller_id == user_id) & (SR.status == "open") & (SR.expires_at > now),
                ),
            )
            .order_by(SR.created_at.desc())
            .limit(200)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def set_status(
        self, row: StoryRequest, status: str, post_id: uuid.UUID | None = None
    ) -> None:
        """@brief Move a request to ``status`` (and link the answer post)."""
        row.status = status
        if post_id is not None:
            row.post_id = post_id
            await self._session.execute(
                update(Post).where(Post.id == post_id).values(story_request_id=row.id)
            )
        await self._session.flush()

    async def answer_post_ok(
        self, post_id: uuid.UUID, teller_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@return True if the post is live, the teller's, and has audio or text."""
        audio = exists().where(
            PostMedia.post_id == Post.id,
            PostMedia.media_id == Media.id,
            Media.content_type.like("audio/%"),
        )
        stmt = select(
            exists().where(
                Post.id == post_id,
                Post.author_id == teller_id,
                Post.community_id == community_id,
                Post.deleted_at.is_(None),
                or_(func.length(func.trim(Post.content)) > 0, audio),
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def claim_reminders(self, community_id: uuid.UUID, now: datetime) -> list[StoryRequest]:
        """@brief Atomically stamp and return open requests due their one reminder."""
        stmt = (
            update(SR)
            .where(
                SR.community_id == community_id,
                SR.status == "open",
                SR.reminded_at.is_(None),
                SR.created_at <= now - REMIND_AFTER,
                SR.expires_at > now,
            )
            .values(reminded_at=now)
            .returning(SR)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def expire_due(self, community_id: uuid.UUID, now: datetime) -> int:
        """@return Number of open/declined requests flipped to ``expired``."""
        stmt = (
            update(SR)
            .where(SR.community_id == community_id, SR.status.in_(LIVE), SR.expires_at <= now)
            .values(status="expired")
        )
        return int((await self._session.execute(stmt)).rowcount or 0)  # type: ignore[attr-defined]

    async def pending_for(
        self, teller_id: uuid.UUID, community_id: uuid.UUID, now: datetime
    ) -> list[Any]:
        """@return (request, asker name) for open unexpired asks the teller can still see."""
        stmt = (
            select(SR, User.display_name)
            .join(User, User.id == SR.asker_id)
            .where(
                SR.community_id == community_id,
                SR.teller_id == teller_id,
                SR.status == "open",
                SR.expires_at > now,
                User.deleted_at.is_(None),
                User.memorialized_at.is_(None),
                ~exists().where(
                    or_(
                        (UserBlock.blocker_id == teller_id) & (UserBlock.blocked_id == SR.asker_id),
                        (UserBlock.blocker_id == SR.asker_id) & (UserBlock.blocked_id == teller_id),
                    )
                ),
            )
            .order_by(SR.created_at)
        )
        return list((await self._session.execute(stmt)).all())

    async def stories_of(
        self,
        author_id: uuid.UUID,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        cursor: datetime | None,
        limit: int,
    ) -> tuple[list[tuple[dict[str, Any], str | None]], datetime | None]:
        """
        @brief Posts by ``author_id`` that answer a request or carry audio,
               filtered by the viewer's post visibility and blocks.
        @return ((enriched post, question) rows newest first, next cursor).
        """
        audio = exists().where(
            PostMedia.post_id == Post.id,
            PostMedia.media_id == Media.id,
            Media.content_type.like("audio/%"),
        )
        stmt = (
            select(Post.id, Post.created_at, SR.question)
            .outerjoin(SR, SR.id == Post.story_request_id)
            .where(
                Post.author_id == author_id,
                post_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
                or_(Post.story_request_id.is_not(None), audio),
            )
            .order_by(Post.created_at.desc())
            .limit(limit + 1)
        )
        if cursor is not None:
            stmt = stmt.where(Post.created_at < cursor)
        rows = (await self._session.execute(stmt)).all()
        nxt = rows[limit - 1][1] if len(rows) > limit else None
        rows = rows[:limit]
        data = await enrich_posts(self._session, [r[0] for r in rows], viewer_id)
        return [(data[r[0]], r[2]) for r in rows if r[0] in data], nxt
