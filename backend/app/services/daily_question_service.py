"""
@file daily_question_service.py
@brief Daily question: bank management, suggestions, firing support and
       answer-to-reveal gating for prompts with ``reveal_after_answer``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError, RateLimitError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.community import Community
from app.models.prompt import Prompt, PromptPost
from app.models.question_bank import QuestionBank
from app.repositories.question_bank_repo import QuestionBankRepository

SUGGESTIONS_PER_DAY = 3
"""@brief Max member suggestions per user per rolling 24h."""

_BANK_PATH = Path(__file__).resolve().parents[2] / "data" / "daily_questions.json"


class DailyQuestionService:
    """@brief Service for the daily-question bank and reveal gating."""

    def __init__(
        self, repo: QuestionBankRepository, community_id: uuid.UUID, session: AsyncSession
    ) -> None:
        self._repo = repo
        self._community_id = community_id
        self._session = session

    async def require_on(self) -> None:
        """@brief Raise FEATURE_DISABLED (404) when the flag is off."""
        community = await self._session.get(Community, self._community_id)
        if community is None:
            raise NotFoundError(_("Community not found"))
        require_feature(community, "daily_question")

    async def is_on(self) -> bool:
        """@brief Whether the daily_question feature is enabled."""
        try:
            await self.require_on()
        except AppError:
            return False
        return True

    async def _ensure_seeded(self) -> None:
        if await self._repo.count_builtin(self._community_id) == 0 and _BANK_PATH.exists():
            texts = json.loads(_BANK_PATH.read_text(encoding="utf-8"))
            await self._repo.seed_builtin(self._community_id, texts)

    async def prepare_fire(self, prompt: Prompt) -> bool:
        """
        @brief Prepare a daily_question prompt to fire: check the flag, resolve an
               author, pick the next question and store it as ``prompt.body``.
        @param prompt The daily_question prompt.
        @return False when it must be skipped (flag off, no author, empty bank).
        """
        if not await self.is_on():
            return False
        if prompt.created_by is None:
            prompt.created_by = await self._repo.first_admin_id(self._community_id)
            if prompt.created_by is None:
                return False
        await self._ensure_seeded()
        sub_id = prompt.id if prompt.scope == "subgroup" else None
        row = await self._repo.next_question(self._community_id, sub_id)
        if row is None:
            return False
        await self._repo.mark_used(row, sub_id)
        prompt.body = row.text
        return True

    async def gate_responses(
        self, prompt: Prompt, pp: PromptPost, viewer_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """
        @brief Locked payload when the viewer may not yet see answers.
        @return ``{"locked": True, "count": n, "items": []}`` or None if visible.
        """
        if not prompt.reveal_after_answer or prompt.created_by == viewer_id:
            return None
        if await self._repo.has_responded(self._community_id, pp.id, viewer_id):
            return None
        count = await self._repo.count_responses(self._community_id, pp.id)
        return {"locked": True, "count": count, "items": []}

    async def can_create(self, user: Any, data: Any) -> bool:
        """@brief Group admins may create subgroup-scoped daily_question prompts."""
        if user.role in ("admin", "owner"):
            return True
        # Group admins get a locked-down shape: daily, group-only, no
        # member broadcast, no event link, short-lived posts.
        return bool(
            data.prompt_type == "daily_question"
            and data.scope == "subgroup"
            and data.subgroup_id is not None
            and data.frequency_type == "daily"
            and not data.notify_members
            and data.linked_event_id is None
            and data.active_days <= 2
            and await self._repo.is_group_admin(self._community_id, data.subgroup_id, user.id)
        )

    # -- bank --

    async def suggest(self, user_id: uuid.UUID, text: str) -> QuestionBank:
        """@brief Member suggestion (pending); 3 per day per user."""
        await self.require_on()
        if await self._repo.count_suggestions_since(self._community_id, user_id) >= (
            SUGGESTIONS_PER_DAY
        ):
            raise RateLimitError(_("You can suggest up to 3 questions per day"))
        return await self._repo.create(
            QuestionBank(
                community_id=self._community_id,
                text=text.strip(),
                source="member",
                status="pending",
                suggested_by=user_id,
            )
        )

    async def add(self, text: str) -> QuestionBank:
        """@brief Admin-added question (approved)."""
        await self.require_on()
        return await self._repo.create(
            QuestionBank(
                community_id=self._community_id,
                text=text.strip(),
                source="admin",
                status="approved",
            )
        )

    async def list_by_status(self, status: str) -> list[QuestionBank]:
        """@brief Admin list by status."""
        await self.require_on()
        return await self._repo.list_by_status(self._community_id, status)

    async def moderate(self, qid: uuid.UUID, status: str) -> QuestionBank:
        """@brief Approve or reject a question (``status`` approved|rejected)."""
        await self.require_on()
        row = await self._repo.get(qid, self._community_id)
        if row is None:
            raise NotFoundError(_("Question not found"))
        row.status = status
        await self._session.flush()
        return row
