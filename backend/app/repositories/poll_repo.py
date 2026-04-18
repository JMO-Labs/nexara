"""
@file poll_repo.py
@brief Repository for polls, options, and votes.

Extends :class:`BaseRepository` with poll-specific queries for options,
vote counts, and vote casting.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult

from app.models.poll import Poll, PollOption, PollVote
from app.repositories.base import BaseRepository


class PollRepository(BaseRepository[Poll]):
    """
    @brief Async repository for poll CRUD with options and votes.

    @param session Async SQLAlchemy session.
    """

    model = Poll

    async def get_with_options(self, poll_id: uuid.UUID) -> Poll | None:
        """
        @brief Fetch a poll by ID (with options loaded via separate query if needed).

        @param poll_id Poll UUID.
        @return Poll instance or None.
        """
        return await self.get_by_id(poll_id)

    async def get_options(self, poll_id: uuid.UUID) -> list[PollOption]:
        """
        @brief Fetch all options for a poll, ordered by position.

        @param poll_id Poll UUID.
        @return List of PollOption instances.
        """
        stmt = (
            select(PollOption)
            .where(PollOption.poll_id == poll_id)
            .order_by(PollOption.position, PollOption.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_vote_counts(self, poll_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """
        @brief Count votes per option for a poll.

        @param poll_id Poll UUID.
        @return Dict mapping option_id -> vote count.
        """
        stmt = (
            select(PollVote.option_id, func.count().label("cnt"))
            .where(PollVote.poll_id == poll_id)
            .group_by(PollVote.option_id)
        )
        result = await self._session.execute(stmt)
        return {row.option_id: row.cnt for row in result.all()}

    async def get_user_votes(self, poll_id: uuid.UUID, user_id: uuid.UUID) -> list[uuid.UUID]:
        """
        @brief Get option IDs the user voted for in this poll.

        @param poll_id Poll UUID.
        @param user_id User UUID.
        @return List of option IDs.
        """
        stmt = select(PollVote.option_id).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def has_user_voted(self, poll_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        @brief Check if the user has voted on this poll.

        @param poll_id Poll UUID.
        @param user_id User UUID.
        @return True if user has voted.
        """
        stmt = (
            select(func.count())
            .select_from(PollVote)
            .where(
                PollVote.poll_id == poll_id,
                PollVote.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def cast_vote(
        self,
        poll_id: uuid.UUID,
        option_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PollVote:
        """
        @brief Record a vote for an option. Replaces existing vote for single-choice.

        @param poll_id Poll UUID.
        @param option_id Option UUID.
        @param user_id User UUID.
        @return The created PollVote instance.
        """
        vote = PollVote(
            poll_id=poll_id,
            option_id=option_id,
            user_id=user_id,
        )
        self._session.add(vote)
        await self._session.flush()
        await self._session.refresh(vote)
        return vote

    async def remove_votes(self, poll_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        @brief Remove all votes by the user on this poll.

        @param poll_id Poll UUID.
        @param user_id User UUID.
        """
        stmt = delete(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def create_options(
        self,
        poll_id: uuid.UUID,
        options_data: list[tuple[str, uuid.UUID | None]],
    ) -> list[PollOption]:
        """
        @brief Create poll options.

        @param poll_id Poll UUID.
        @param options_data List of (label, image_media_id) tuples.
        @return List of created PollOption instances.
        """
        created = []
        for i, (label, image_media_id) in enumerate(options_data):
            option = PollOption(
                poll_id=poll_id,
                label=label,
                image_media_id=image_media_id,
                position=i,
            )
            self._session.add(option)
            created.append(option)
        await self._session.flush()
        for opt in created:
            await self._session.refresh(opt)
        return created

    async def close_expired(self) -> int:
        """
        @brief Close all polls past their expires_at timestamp.

        @return Number of polls closed.
        """
        now = datetime.now(UTC)
        stmt = (
            update(Poll)
            .where(
                Poll.expires_at.isnot(None),
                Poll.expires_at < now,
                Poll.closed.is_(False),
            )
            .values(closed=True)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return cast(CursorResult[Any], result).rowcount or 0
