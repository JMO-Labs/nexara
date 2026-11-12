"""
@file suggestion_service.py
@brief Generates prompt and poll suggestions with the AI provider for admin review.
"""

from __future__ import annotations

import uuid

import structlog

from app.models.suggestion import Suggestion
from app.repositories.suggestion_repo import SuggestionRepository
from app.services.ai.provider import AIProvider

logger = structlog.get_logger(__name__)

MAX_PROMPT_LEN = 100
PROMPT_COUNT = 5
POLL_OPTIONS = 4


def _lines(text: str) -> list[str]:
    """@brief Split into non-empty lines, stripping list bullets/numbering."""
    out = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*•").strip()
        if line[:2].rstrip(".)").isdigit() and line[1:2] in ".)":
            line = line[2:].strip()
        if line:
            out.append(line)
    return out


class SuggestionService:
    """@brief AI suggestion generation; AI failures are logged and skipped."""

    def __init__(self, repo: SuggestionRepository, provider: AIProvider | None) -> None:
        self._repo = repo
        self._provider = provider

    async def _complete(self, prompt: str, max_tokens: int) -> str | None:
        if self._provider is None:
            return None
        try:
            text, _cost, _tokens = await self._provider.complete(prompt, max_tokens, 0.8)
        except Exception as exc:  # AI must never fail the endpoint
            logger.warning("suggestion_ai_failed", error=str(exc))
            return None
        return text

    async def generate_prompt_suggestions(self, community_id: uuid.UUID) -> list[str]:
        """
        @brief Suggest up to 5 conversation prompts (<=100 chars) and store them.
        @param community_id Community scope.
        @return Stored prompt texts; empty when no context, no AI, or AI failure.
        """
        posts = await self._repo.recent_post_snippets(community_id, 10)
        interests = await self._repo.top_interests(community_id, 5)
        events = await self._repo.upcoming_event_titles(community_id, 5)
        if not (posts or interests or events):
            return []
        prompt = (
            f"Given community posts [{' | '.join(posts)}], interests [{', '.join(interests)}], "
            f"events [{', '.join(events)}], suggest {PROMPT_COUNT} engaging prompts, "
            f"max {MAX_PROMPT_LEN} chars each. Format: one per line."
        )
        text = await self._complete(prompt, 400)
        if not text:
            return []
        items = [s[:MAX_PROMPT_LEN] for s in _lines(text)[:PROMPT_COUNT]]
        for item in items:
            await self._repo.create(community_id, "prompt", {"text": item})
        return items

    async def generate_poll_suggestions(
        self, community_id: uuid.UUID, topic: str
    ) -> tuple[str, list[str]] | None:
        """
        @brief Suggest a poll (question + 4 options) about ``topic`` and store it.
        @return (question, options) or None on AI failure / malformed output.
        """
        prompt = (
            f"Generate poll about '{topic}' for family/community. "
            "Format: QUESTION\nOPTION1\nOPTION2\nOPTION3\nOPTION4"
        )
        text = await self._complete(prompt, 300)
        lines = _lines(text) if text else []
        if len(lines) < POLL_OPTIONS + 1:
            return None
        question, options = lines[0], lines[1 : POLL_OPTIONS + 1]
        await self._repo.create(
            community_id, "poll", {"question": question, "options": options, "topic": topic}
        )
        return question, options

    async def list_pending(
        self, community_id: uuid.UUID, type: str | None = None, limit: int = 10, offset: int = 0
    ) -> list[Suggestion]:
        """@brief Pending suggestions for admin review, newest first."""
        return await self._repo.list_pending(community_id, type, limit, offset)

    async def approve(
        self, suggestion_id: uuid.UUID, approver_id: uuid.UUID, community_id: uuid.UUID
    ) -> Suggestion:
        """@brief Approve a pending suggestion. @throws NotFoundError, ConflictError."""
        return await self._repo.approve(suggestion_id, approver_id, community_id)

    async def reject(self, suggestion_id: uuid.UUID, community_id: uuid.UUID) -> Suggestion:
        """@brief Reject a pending suggestion. @throws NotFoundError, ConflictError."""
        return await self._repo.reject(suggestion_id, community_id)
