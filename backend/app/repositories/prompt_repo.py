"""
@file prompt_repo.py
@brief Repository for prompts and prompt-post tracking.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import and_, func, or_, select

from app.models.prompt import Prompt, PromptPost
from app.repositories.base import BaseRepository


class PromptRepository(BaseRepository[Prompt]):
    """@brief Async repo for prompts and prompt firing tracking."""

    model = Prompt

    async def list_enabled(self, community_id: uuid.UUID) -> list[Prompt]:
        """@brief List all enabled prompts in a community (used by Beat)."""
        stmt = select(Prompt).where(
            Prompt.community_id == community_id,
            Prompt.is_enabled.is_(True),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_admin(self, community_id: uuid.UUID) -> list[Prompt]:
        """@brief List all prompts (admin view, including disabled + builtins)."""
        stmt = (
            select(Prompt)
            .where(Prompt.community_id == community_id)
            .order_by(Prompt.is_enabled.desc(), Prompt.title.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_post_for_today(self, prompt_id: uuid.UUID, fired_at: date) -> PromptPost | None:
        """@brief Idempotency: fetch existing PromptPost for (prompt, date)."""
        stmt = select(PromptPost).where(
            PromptPost.prompt_id == prompt_id,
            PromptPost.fired_at == fired_at,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_pinned(self, community_id: uuid.UUID, now: datetime) -> int:
        """@brief Count currently-pinned (active, not finalised) prompt posts."""
        stmt = (
            select(func.count())
            .select_from(PromptPost)
            .where(
                PromptPost.community_id == community_id,
                PromptPost.is_finalised.is_(False),
                PromptPost.expires_at > now,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_expired_unfinalised(
        self, community_id: uuid.UUID, now: datetime
    ) -> list[PromptPost]:
        """@brief List prompt posts past expiry that need a summary."""
        stmt = select(PromptPost).where(
            PromptPost.community_id == community_id,
            PromptPost.is_finalised.is_(False),
            PromptPost.expires_at <= now,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(self, community_id: uuid.UUID, now: datetime) -> list[PromptPost]:
        """@brief List currently-active (pinned) prompt posts."""
        stmt = (
            select(PromptPost)
            .where(
                PromptPost.community_id == community_id,
                or_(
                    PromptPost.is_finalised.is_(False),
                    and_(PromptPost.expires_at > now, PromptPost.is_finalised.is_(False)),
                ),
                PromptPost.expires_at > now,
            )
            .order_by(PromptPost.fired_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_prompt_post(self, pp: PromptPost) -> PromptPost:
        """@brief Persist a prompt-post tracker row."""
        self._session.add(pp)
        await self._session.flush()
        await self._session.refresh(pp)
        return pp

    async def increment_response_count(self, prompt_post_id: uuid.UUID) -> None:
        """@brief Bump response_count by one (called when comment is added)."""
        from sqlalchemy import update

        await self._session.execute(
            update(PromptPost)
            .where(PromptPost.id == prompt_post_id)
            .values(response_count=PromptPost.response_count + 1)
        )
        await self._session.flush()

    async def get_prompt_post(self, pp_id: uuid.UUID) -> PromptPost | None:
        """@brief Fetch a prompt-post tracker by id."""
        stmt = select(PromptPost).where(PromptPost.id == pp_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def finalise(
        self,
        prompt_post: PromptPost,
        summary_post_id: uuid.UUID | None,
    ) -> PromptPost:
        """@brief Mark a prompt post as finalised with the summary post id."""
        prompt_post.is_finalised = True
        prompt_post.summary_post_id = summary_post_id
        await self._session.flush()
        return prompt_post
