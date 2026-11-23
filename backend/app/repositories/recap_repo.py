"""
@file recap_repo.py
@brief Recap email lookups: who might be due, the send stamp, and
       yesterday's community-wide daily question.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.models.user import User
from app.models.user_settings import UserSettings


class RecapCandidate(NamedTuple):
    """@brief A user who has not turned the recap off."""

    user_id: uuid.UUID
    timezone: str | None
    dnd_timezone: str | None
    cadence: str
    last_sent_at: datetime | None


class RecapRepository:
    """@brief Community-scoped recap reads and the send stamp."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def candidates(self, community_id: uuid.UUID) -> list[RecapCandidate]:
        """@return Active, non-bot users with an email whose cadence is not 'off'."""
        stmt = (
            select(
                User.id,
                User.timezone,
                UserSettings.dnd_timezone,
                UserSettings.recap_cadence,
                UserSettings.recap_last_sent_at,
            )
            .join(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.is_bot.is_(False),
                User.email != "",
                UserSettings.recap_cadence != "off",
            )
        )
        return [RecapCandidate(*r) for r in (await self._session.execute(stmt)).all()]

    async def stamp_sent(self, user_id: uuid.UUID, now: datetime) -> None:
        """@brief Record ``recap_last_sent_at`` (call before enqueueing)."""
        await self._session.execute(
            update(UserSettings)
            .where(UserSettings.user_id == user_id)
            .values(recap_last_sent_at=now)
        )

    async def yesterday_daily(
        self, community_id: uuid.UUID, day: date
    ) -> tuple[uuid.UUID, str, int] | None:
        """
        @param community_id Community scope.
        @param day Date the question was fired.
        @return ``(post_id, question text, response_count)`` of the community-wide
                daily question, or None. Group-scoped questions are never returned.
        """
        stmt = (
            select(PromptPost.post_id, Post.content, PromptPost.response_count)
            .join(Prompt, Prompt.id == PromptPost.prompt_id)
            .join(Post, Post.id == PromptPost.post_id)
            .where(
                PromptPost.community_id == community_id,
                PromptPost.fired_at == day,
                Prompt.prompt_type == "daily_question",
                Prompt.scope == "community",
                Post.deleted_at.is_(None),
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1] or "", row[2]) if row else None

    async def cadence(self, user_id: uuid.UUID) -> str:
        """@return The user's recap cadence (``weekly`` when no settings row)."""
        stmt = select(UserSettings.recap_cadence).where(UserSettings.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none() or "weekly"
