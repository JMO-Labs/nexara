"""
@file nudge_repo.py
@brief Data access for nudges.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, exists, or_, select

from app.models.moderation import UserBlock
from app.models.nudge import Nudge
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository

RATE_WINDOW = timedelta(hours=24)
INACTIVE_AFTER = timedelta(days=14)
GENTLE_COOLDOWN = timedelta(days=7)


class NudgeRepository(BaseRepository[Nudge]):
    """@brief Repository for nudges (soft-deleted via deleted_at)."""

    model = Nudge

    async def create_nudge(
        self, sender_id: uuid.UUID, target_id: uuid.UUID, nudge_type: str, community_id: uuid.UUID
    ) -> Nudge:
        """@brief Insert a nudge. @return The created Nudge."""
        return await self.create(
            Nudge(
                sender_id=sender_id,
                target_id=target_id,
                nudge_type=nudge_type,
                community_id=community_id,
            )
        )

    async def has_recent_user_nudge(
        self, sender_id: uuid.UUID, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief True if sender nudged target within the last 24h (soft-deleted rows count)."""
        stmt = select(
            exists().where(
                Nudge.sender_id == sender_id,
                Nudge.target_id == target_id,
                Nudge.community_id == community_id,
                Nudge.nudge_type == "user_initiated",
                Nudge.created_at > datetime.now(UTC) - RATE_WINDOW,
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def is_blocked(
        self, sender_id: uuid.UUID, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief True if either user has blocked the other."""
        stmt = select(
            exists().where(
                UserBlock.community_id == community_id,
                or_(
                    and_(UserBlock.blocker_id == target_id, UserBlock.blocked_id == sender_id),
                    and_(UserBlock.blocker_id == sender_id, UserBlock.blocked_id == target_id),
                ),
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def find_gentle_candidates(self, community_id: uuid.UUID) -> list[uuid.UUID]:
        """
        @brief Opted-in users inactive > 14 days with no gentle nudge in the last 7 days.
        @return User ids.
        """
        now = datetime.now(UTC)
        recent = exists().where(
            Nudge.target_id == User.id,
            Nudge.nudge_type == "gentle",
            Nudge.created_at > now - GENTLE_COOLDOWN,
        )
        stmt = (
            select(User.id)
            .join(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.deleted_at.is_(None),
                User.last_seen_at.is_not(None),
                User.last_seen_at < now - INACTIVE_AFTER,
                UserSettings.receive_gentle_nudges.is_(True),
                ~recent,
            )
        )
        return list((await self._session.execute(stmt)).scalars().all())
