"""
@file question_bank_repo.py
@brief Repository for the daily-question bank.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.question_bank import QuestionBank, QuestionBankUse
from app.models.subgroup import SubgroupMember
from app.models.user import User


class QuestionBankRepository:
    """@brief Async repo for QuestionBank rows (always community-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: QuestionBank) -> QuestionBank:
        """@brief Insert a row, flush and refresh it."""
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, qid: uuid.UUID, community_id: uuid.UUID) -> QuestionBank | None:
        """@brief Fetch one row by id within the community."""
        stmt = select(QuestionBank).where(
            QuestionBank.id == qid, QuestionBank.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(self, community_id: uuid.UUID, status: str) -> list[QuestionBank]:
        """@brief List rows with a status, oldest first."""
        stmt = (
            select(QuestionBank)
            .where(QuestionBank.community_id == community_id, QuestionBank.status == status)
            .order_by(QuestionBank.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_builtin(self, community_id: uuid.UUID) -> int:
        """@brief Number of builtin rows (0 means not yet seeded)."""
        stmt = (
            select(func.count())
            .select_from(QuestionBank)
            .where(QuestionBank.community_id == community_id, QuestionBank.source == "builtin")
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def seed_builtin(self, community_id: uuid.UUID, texts: list[str]) -> None:
        """@brief Bulk-insert approved builtin questions."""
        self._session.add_all(
            QuestionBank(community_id=community_id, text=t, source="builtin", status="approved")
            for t in texts
        )
        await self._session.flush()

    async def count_suggestions_since(
        self, community_id: uuid.UUID, user_id: uuid.UUID, hours: int = 24
    ) -> int:
        """@brief Member suggestions by a user in the last ``hours``."""
        since = datetime.now(UTC) - timedelta(hours=hours)
        stmt = (
            select(func.count())
            .select_from(QuestionBank)
            .where(
                QuestionBank.community_id == community_id,
                QuestionBank.suggested_by == user_id,
                QuestionBank.source == "member",
                QuestionBank.created_at >= since,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def _pick(
        self, community_id: uuid.UUID, prompt_id: uuid.UUID | None
    ) -> QuestionBank | None:
        is_builtin = QuestionBank.source == "builtin"
        stmt = select(QuestionBank).where(
            QuestionBank.community_id == community_id, QuestionBank.status == "approved"
        )
        if prompt_id is None:
            stmt = stmt.where(QuestionBank.used_at.is_(None))
        else:
            used = select(QuestionBankUse.question_id).where(QuestionBankUse.prompt_id == prompt_id)
            stmt = stmt.where(QuestionBank.id.not_in(used))
        stmt = stmt.order_by(
            is_builtin, case((is_builtin, func.random()), else_=0), QuestionBank.created_at
        ).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_question(
        self, community_id: uuid.UUID, prompt_id: uuid.UUID | None = None
    ) -> QuestionBank | None:
        """
        @brief Next unused approved question: admin/member first (oldest first),
               then random builtin. Recycles builtin once when exhausted.
        @param community_id Community scope.
        @param prompt_id Group prompt id: track use in ``question_bank_uses``
               instead of ``question_bank.used_at``.
        @return The question or None when the bank is empty.
        """
        row = await self._pick(community_id, prompt_id)
        if row is not None:
            return row
        builtin_ids = select(QuestionBank.id).where(
            QuestionBank.community_id == community_id, QuestionBank.source == "builtin"
        )
        if prompt_id is None:
            await self._session.execute(
                update(QuestionBank).where(QuestionBank.id.in_(builtin_ids)).values(used_at=None)
            )
        else:
            await self._session.execute(
                delete(QuestionBankUse).where(
                    QuestionBankUse.prompt_id == prompt_id,
                    QuestionBankUse.question_id.in_(builtin_ids),
                )
            )
        return await self._pick(community_id, prompt_id)

    async def mark_used(self, row: QuestionBank, prompt_id: uuid.UUID | None) -> None:
        """@brief Record that a question was asked (global or per-prompt)."""
        if prompt_id is None:
            row.used_at = datetime.now(UTC)
        else:
            self._session.add(QuestionBankUse(prompt_id=prompt_id, question_id=row.id))
        await self._session.flush()

    # -- prompt-response helpers (answer-to-reveal) --

    async def count_responses(self, community_id: uuid.UUID, prompt_post_id: uuid.UUID) -> int:
        """@brief Count live replies to a prompt post."""
        stmt = (
            select(func.count())
            .select_from(Post)
            .where(
                Post.community_id == community_id,
                Post.reply_to_prompt_id == prompt_post_id,
                Post.deleted_at.is_(None),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def has_responded(
        self, community_id: uuid.UUID, prompt_post_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """@brief True when the user has a live reply to the prompt post."""
        stmt = (
            select(Post.id)
            .where(
                Post.community_id == community_id,
                Post.reply_to_prompt_id == prompt_post_id,
                Post.author_id == user_id,
                Post.deleted_at.is_(None),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def first_admin_id(self, community_id: uuid.UUID) -> uuid.UUID | None:
        """@brief Oldest admin/owner user (author for system-fired posts)."""
        stmt = (
            select(User.id)
            .where(User.community_id == community_id, User.role.in_(("admin", "owner")))
            .order_by(User.created_at)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def is_group_admin(
        self, community_id: uuid.UUID, subgroup_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """@brief True when the user is owner/moderator of the subgroup."""
        stmt = select(SubgroupMember.user_id).where(
            SubgroupMember.community_id == community_id,
            SubgroupMember.subgroup_id == subgroup_id,
            SubgroupMember.user_id == user_id,
            SubgroupMember.role.in_(("owner", "moderator")),
        )
        return (await self._session.execute(stmt)).first() is not None
