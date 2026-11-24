"""
@file countdown_repo.py
@brief Countdown persistence: scoped reads, follows, feed post, reminder ledger.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.countdown import Countdown, CountdownFollower, CountdownReminderSent
from app.models.post import Post
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.repositories.visibility_preds import my_subgroup_ids, not_blocked


def countdown_visible(viewer_id: Any, community_id: uuid.UUID) -> Any:
    """@brief Live countdown the viewer may read (community / their group / own private)."""
    return and_(
        Countdown.community_id == community_id,
        Countdown.deleted_at.is_(None),
        or_(
            Countdown.visibility == "community",
            and_(
                Countdown.visibility == "subgroup",
                Countdown.subgroup_id.in_(my_subgroup_ids(viewer_id)),
            ),
            and_(Countdown.visibility == "private", Countdown.author_id == viewer_id),
        ),
        not_blocked(Countdown.author_id, viewer_id),
    )


class CountdownRepository:
    """@brief Data access for countdowns (every query community-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def is_member(self, subgroup_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Whether the user belongs to the subgroup."""
        stmt = select(SubgroupMember.user_id).where(
            SubgroupMember.subgroup_id == subgroup_id, SubgroupMember.user_id == user_id
        )
        return (await self._s.execute(stmt)).first() is not None

    async def add(self, c: Countdown, post: Post) -> Countdown:
        """@brief Insert the countdown and its feed post, linking both ways."""
        self._s.add(c)
        await self._s.flush()
        post.countdown_id = c.id
        self._s.add(post)
        await self._s.flush()
        c.post_id = post.id
        await self._s.flush()
        return c

    async def get(self, cid: uuid.UUID, countdown_id: uuid.UUID) -> Countdown | None:
        """@brief Live countdown by id (no visibility check)."""
        stmt = select(Countdown).where(
            Countdown.id == countdown_id,
            Countdown.community_id == cid,
            Countdown.deleted_at.is_(None),
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_visible(
        self, cid: uuid.UUID, countdown_id: uuid.UUID, viewer_id: uuid.UUID
    ) -> Countdown | None:
        """@brief Countdown by id if the viewer may see it."""
        stmt = select(Countdown).where(
            Countdown.id == countdown_id, countdown_visible(viewer_id, cid)
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def list_visible(self, cid: uuid.UUID, viewer_id: uuid.UUID) -> list[Countdown]:
        """@brief All countdowns the viewer may see, soonest target first."""
        stmt = (
            select(Countdown)
            .where(countdown_visible(viewer_id, cid))
            .order_by(Countdown.target_date, Countdown.created_at)
        )
        return list((await self._s.execute(stmt)).scalars())

    async def list_following(self, cid: uuid.UUID, viewer_id: uuid.UUID) -> list[Countdown]:
        """@brief Visible countdowns the viewer follows."""
        stmt = (
            select(Countdown)
            .join(CountdownFollower, CountdownFollower.countdown_id == Countdown.id)
            .where(CountdownFollower.user_id == viewer_id, countdown_visible(viewer_id, cid))
        )
        return list((await self._s.execute(stmt)).scalars())

    async def apply(self, c: Countdown, data: dict[str, Any]) -> Countdown:
        """@brief Set fields on a countdown."""
        for k, v in data.items():
            setattr(c, k, v)
        await self._s.flush()
        return c

    async def set_post_content(self, post_id: uuid.UUID, content: str) -> None:
        """@brief Update the feed card text."""
        await self._s.execute(update(Post).where(Post.id == post_id).values(content=content))

    async def soft_delete(self, c: Countdown) -> None:
        """@brief Soft-delete the countdown and its feed post."""
        now = datetime.now(UTC)
        c.deleted_at = now
        if c.post_id is not None:
            await self._s.execute(
                update(Post)
                .where(Post.id == c.post_id, Post.deleted_at.is_(None))
                .values(deleted_at=now)
            )
        await self._s.flush()

    async def follow(self, countdown_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Idempotently follow."""
        await self._s.execute(
            insert(CountdownFollower)
            .values(countdown_id=countdown_id, user_id=user_id)
            .on_conflict_do_nothing()
        )

    async def unfollow(self, countdown_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Idempotently unfollow."""
        await self._s.execute(
            delete(CountdownFollower).where(
                CountdownFollower.countdown_id == countdown_id,
                CountdownFollower.user_id == user_id,
            )
        )

    async def follow_info(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID
    ) -> tuple[dict[uuid.UUID, int], set[uuid.UUID]]:
        """@return (follower counts by countdown, ids the viewer follows)."""
        if not ids:
            return {}, set()
        rows = await self._s.execute(
            select(CountdownFollower.countdown_id, func.count())
            .where(CountdownFollower.countdown_id.in_(ids))
            .group_by(CountdownFollower.countdown_id)
        )
        counts = {cid: n for cid, n in rows.all()}
        mine = await self._s.execute(
            select(CountdownFollower.countdown_id).where(
                CountdownFollower.countdown_id.in_(ids), CountdownFollower.user_id == viewer_id
            )
        )
        return counts, set(mine.scalars())

    async def reminder_targets(
        self, cid: uuid.UUID
    ) -> list[tuple[Countdown, uuid.UUID, str | None]]:
        """@return (countdown, follower id, follower timezone) for every live follow."""
        stmt = (
            select(Countdown, User.id, User.timezone)
            .join(CountdownFollower, CountdownFollower.countdown_id == Countdown.id)
            .join(User, User.id == CountdownFollower.user_id)
            .where(
                User.deleted_at.is_(None),
                User.community_id == cid,
                countdown_visible(User.id, cid),
            )
        )
        return [(c, uid, tz) for c, uid, tz in (await self._s.execute(stmt)).all()]

    async def mark_sent(
        self, countdown_id: uuid.UUID, user_id: uuid.UUID, kind: str, occurrence: date
    ) -> bool:
        """@return True if newly recorded (False = already sent)."""
        stmt = (
            insert(CountdownReminderSent)
            .values(countdown_id=countdown_id, user_id=user_id, kind=kind, occurrence=occurrence)
            .on_conflict_do_nothing()
            .returning(CountdownReminderSent.user_id)
        )
        return (await self._s.execute(stmt)).first() is not None
