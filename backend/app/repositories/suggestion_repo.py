"""
@file suggestion_repo.py
@brief Data access for AI suggestions plus the context queries used to generate them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError
from app.core.i18n import _
from app.models.event import Event
from app.models.interest import UserInterest
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.models.user import User
from app.repositories.base import BaseRepository

SNIPPET_LEN = 140


class SuggestionRepository(BaseRepository[Suggestion]):
    """@brief Repository for suggestions (community scoped)."""

    model = Suggestion

    # create() takes extra domain args, narrower than base
    async def create(  # type: ignore[override]
        self, community_id: uuid.UUID, type: str, content: dict[str, Any]
    ) -> Suggestion:
        """@brief Insert a pending suggestion. @return The created Suggestion."""
        return await super().create(
            Suggestion(community_id=community_id, type=type, content=content)
        )

    async def list_pending(
        self, community_id: uuid.UUID, type: str | None = None, limit: int = 10, offset: int = 0
    ) -> list[Suggestion]:
        """@brief Pending (neither approved nor rejected) suggestions, newest first."""
        stmt = select(Suggestion).where(
            Suggestion.community_id == community_id,
            Suggestion.approved_at.is_(None),
            Suggestion.rejected_at.is_(None),
        )
        if type:
            stmt = stmt.where(Suggestion.type == type)
        stmt = stmt.order_by(Suggestion.created_at.desc()).limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars().all())

    async def _get_pending(self, suggestion_id: uuid.UUID, community_id: uuid.UUID) -> Suggestion:
        s = await self.get_by_id(suggestion_id, community_id)
        if s is None:
            raise NotFoundError(_("Suggestion not found"))
        if s.approved_at is not None or s.rejected_at is not None:
            raise ConflictError(_("Suggestion already reviewed"))
        return s

    async def approve(
        self, suggestion_id: uuid.UUID, approver_id: uuid.UUID, community_id: uuid.UUID
    ) -> Suggestion:
        """@brief Mark approved. @throws NotFoundError, ConflictError if already reviewed."""
        s = await self._get_pending(suggestion_id, community_id)
        s.approved_at = datetime.now(UTC)
        s.approved_by = approver_id
        await self._session.flush()
        await self._session.refresh(s)
        return s

    async def reject(self, suggestion_id: uuid.UUID, community_id: uuid.UUID) -> Suggestion:
        """@brief Mark rejected. @throws NotFoundError, ConflictError if already reviewed."""
        s = await self._get_pending(suggestion_id, community_id)
        s.rejected_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(s)
        return s

    async def recent_post_snippets(self, community_id: uuid.UUID, limit: int) -> list[str]:
        """@brief Content snippets of the latest public community posts."""
        stmt = (
            select(Post.content)
            .where(
                Post.community_id == community_id,
                Post.deleted_at.is_(None),
                Post.visibility == "community",
                Post.recipient_id.is_(None),
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        return [c[:SNIPPET_LEN] for c in (await self._session.execute(stmt)).scalars().all()]

    async def top_interests(self, community_id: uuid.UUID, limit: int) -> list[str]:
        """@brief Most common interest values among community members."""
        stmt = (
            select(UserInterest.value)
            .join(User, User.id == UserInterest.user_id)
            .where(User.community_id == community_id)
            .group_by(UserInterest.value)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def upcoming_event_titles(self, community_id: uuid.UUID, limit: int) -> list[str]:
        """@brief Titles of the next upcoming community-visible events (no private/subgroup)."""
        stmt = (
            select(Event.title)
            .where(
                Event.community_id == community_id,
                Event.starts_at >= datetime.now(UTC),
                Event.visibility == "community",
                Event.source_removed.is_(False),
            )
            .order_by(Event.starts_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
