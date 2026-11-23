"""
@file reconnect_repo.py
@brief Queries behind reconnect nudges: stale-relative pick, snoozes, prefs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, case, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.chat import ChatMessage, DirectMessageParticipant
from app.models.moderation import UserBlock
from app.models.nudge import Nudge
from app.models.post import Comment, Post
from app.models.reconnect import ReconnectSnooze
from app.models.relation import Relation
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.relation_repo import FAMILY_KINDS

COOLDOWN = timedelta(days=7)
SNOOZE_FOR = timedelta(days=90)
DEFAULT_DAYS = 30


def _either(col_a: Any, a: object, col_b: Any, b: object) -> ColumnElement[bool]:
    """@brief ``col_a = a AND col_b = b`` (one direction of a pair)."""
    return and_(col_a == a, col_b == b)


class ReconnectRepository:
    """@brief Read/write helpers for reconnect nudges (all community scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def eligible_users(self, community_id: uuid.UUID, now: datetime) -> list[uuid.UUID]:
        """@brief Active users with reminders on and no reconnect nudge in 7 days."""
        recent = exists().where(
            Nudge.community_id == community_id,
            Nudge.target_id == User.id,
            Nudge.nudge_type == "reconnect",
            Nudge.created_at > now - COOLDOWN,
        )
        stmt = (
            select(User.id)
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.is_active.is_(True),
                User.is_bot.is_(False),
                User.deleted_at.is_(None),
                User.memorialized_at.is_(None),
                func.coalesce(UserSettings.reconnect_nudges, True).is_(True),
                ~recent,
            )
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def prefs(self, user_id: uuid.UUID, community_id: uuid.UUID) -> tuple[bool, int]:
        """@return ``(enabled, days)``; defaults when no settings row exists."""
        stmt = select(UserSettings.reconnect_nudges, UserSettings.reconnect_days).where(
            UserSettings.user_id == user_id, UserSettings.community_id == community_id
        )
        row = (await self._session.execute(stmt)).first()
        return (True, DEFAULT_DAYS) if row is None else (bool(row[0]), int(row[1]))

    async def has_recent_reconnect(
        self, user_id: uuid.UUID, community_id: uuid.UUID, now: datetime
    ) -> bool:
        """@brief A reconnect nudge was sent to the user within the last 7 days."""
        stmt = select(
            exists().where(
                Nudge.community_id == community_id,
                Nudge.target_id == user_id,
                Nudge.nudge_type == "reconnect",
                Nudge.created_at > now - COOLDOWN,
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def stalest_relative(
        self, user_id: uuid.UUID, community_id: uuid.UUID, cutoff: datetime, now: datetime
    ) -> uuid.UUID | None:
        """
        @brief The confirmed family member with the longest quiet gap, in one query.

        Last contact = latest of: DM message either way, comment on the other's
        post either way, kudos either way; the relation's confirmation time is the
        floor so brand-new relations are not nagged. Excludes blocked (either
        direction), inactive, deleted, memorialized and snoozed people.
        @param cutoff ``now - reconnect_days``; only gaps older than this qualify.
        @return Relative's user id or None.
        """
        other = case(
            (Relation.from_user_id == user_id, Relation.to_user_id), else_=Relation.from_user_id
        )
        p1, p2 = aliased(DirectMessageParticipant), aliased(DirectMessageParticipant)
        dm = (
            select(func.max(ChatMessage.created_at))
            .join(p1, p1.channel_id == ChatMessage.channel_id)
            .join(p2, p2.channel_id == ChatMessage.channel_id)
            .where(p1.user_id == user_id, p2.user_id == other)
            .correlate(Relation)
            .scalar_subquery()
        )
        cm = (
            select(func.max(Comment.created_at))
            .join(Post, Post.id == Comment.post_id)
            .where(
                Post.deleted_at.is_(None),
                or_(
                    _either(Comment.author_id, user_id, Post.author_id, other),
                    _either(Comment.author_id, other, Post.author_id, user_id),
                ),
            )
            .correlate(Relation)
            .scalar_subquery()
        )
        kd = (
            select(func.max(Post.created_at))
            .where(
                Post.recipient_id.is_not(None),
                Post.deleted_at.is_(None),
                or_(
                    _either(Post.author_id, user_id, Post.recipient_id, other),
                    _either(Post.author_id, other, Post.recipient_id, user_id),
                ),
            )
            .correlate(Relation)
            .scalar_subquery()
        )
        last = func.greatest(dm, cm, kd, func.coalesce(Relation.confirmed_at, Relation.created_at))
        blocked = exists().where(
            UserBlock.community_id == community_id,
            or_(
                _either(UserBlock.blocker_id, user_id, UserBlock.blocked_id, other),
                _either(UserBlock.blocker_id, other, UserBlock.blocked_id, user_id),
            ),
        )
        snoozed = exists().where(
            ReconnectSnooze.user_id == user_id,
            ReconnectSnooze.target_id == other,
            ReconnectSnooze.until > now,
        )
        stmt = (
            select(User.id)
            .select_from(Relation)
            .join(User, User.id == other)
            .where(
                Relation.community_id == community_id,
                Relation.status == "confirmed",
                Relation.kind.in_(FAMILY_KINDS),
                Relation.to_user_id.is_not(None),
                or_(Relation.from_user_id == user_id, Relation.to_user_id == user_id),
                User.community_id == community_id,
                User.is_active.is_(True),
                User.is_bot.is_(False),
                User.deleted_at.is_(None),
                User.memorialized_at.is_(None),
                last < cutoff,
                ~blocked,
                ~snoozed,
            )
            .order_by(last.asc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def snooze(self, user_id: uuid.UUID, target_id: uuid.UUID, now: datetime) -> datetime:
        """@brief Upsert a 90-day snooze. @return The new ``until``."""
        until = now + SNOOZE_FOR
        stmt = insert(ReconnectSnooze).values(user_id=user_id, target_id=target_id, until=until)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "target_id"], set_={"until": until}
        )
        await self._session.execute(stmt)
        return until

    async def record(self, user_id: uuid.UUID, community_id: uuid.UUID, now: datetime) -> None:
        """@brief Log a sent reconnect nudge (sender == target, like gentle nudges)."""
        self._session.add(
            Nudge(
                sender_id=user_id,
                target_id=user_id,
                nudge_type="reconnect",
                community_id=community_id,
                created_at=now,
            )
        )
        await self._session.flush()
