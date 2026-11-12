"""
@file sassybot_service.py
@brief Sassybot: generates playful AI comments on posts (opt-out, sass levels).
"""

from __future__ import annotations

import random
import re
import uuid

from app.repositories.sassybot_repo import SassybotRepository
from app.services.ai.provider import AIProvider
from app.services.storage.base import StorageBackend

#: Maximum Sassybot comments per post thread.
MAX_THREAD_COMMENTS = 3
MAX_COMMENT_CHARS = 200
_CONTENT_CHARS = 500
_SASS_TEXT = {1: "mild", 2: "moderate", 3: "spicy"}
_VISION_PROMPT = "Describe this image in one short sentence."
_MENTION_RE = re.compile(r"(?<![\w@])@sassybot\b", re.IGNORECASE)


def wants_sassybot(content: str) -> bool:
    """
    @brief Whether content @mentions Sassybot.
    @param content Post or comment text.
    @return True if @sassybot is mentioned.
    """
    return bool(_MENTION_RE.search(content))


class SassybotService:
    """@brief Builds prompts and generates Sassybot comments."""

    def __init__(
        self,
        repo: SassybotRepository,
        provider: AIProvider,
        storage: StorageBackend,
        bot_user_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._provider = provider
        self._storage = storage
        self._bot_id = bot_user_id

    async def generate_comment(self, post_id: uuid.UUID, community_id: uuid.UUID) -> str | None:
        """
        @brief Generate a comment for a post.
        @param post_id Post UUID.
        @param community_id Community UUID.
        @return Comment text, or None if the post is missing or the author opted out.
        @throws AIError on provider failure (callers skip).
        """
        found = await self._repo.get_post_and_author(post_id, community_id)
        if found is None:
            return None
        post, author = found
        if author.sassybot_opt_out:
            return None
        community = await self._repo.get_community(community_id)
        level = community.sassybot_sass_level if community else 2
        sass = _SASS_TEXT.get(level, "moderate")

        descriptions: list[str] = []
        for media in await self._repo.get_images(post_id):
            data = await self._storage.get(media.storage_key)
            text, _, _ = await self._provider.vision(data, _VISION_PROMPT, 100)
            descriptions.append(text.strip())
        vision = (
            "The post has images: " + "; ".join(descriptions) + "." if descriptions else ""
        )

        prompt = (
            f"Generate a {sass} witty comment on this post: "
            f"[{post.content[:_CONTENT_CHARS]}] (posted {post.created_at.isoformat()}). "
            f"{vision} Keep under {MAX_COMMENT_CHARS} chars. Be playful, never mean. Sassybot."
        )
        text, _, _ = await self._provider.complete(prompt, 100, 0.9)
        text = text.strip()
        return text[:MAX_COMMENT_CHARS] if text else None

    async def should_trigger(self, post_id: uuid.UUID) -> bool:
        """
        @brief Probability gate; always False in invoke-only mode.
        @param post_id Post UUID.
        @return True if Sassybot should comment.
        """
        cid = await self._repo.get_community_id_for_post(post_id)
        if cid is None:
            return False
        community = await self._repo.get_community(cid)
        if community is None or community.sassybot_invoke_only:
            return False
        return random.uniform(0, 100) < community.sassybot_probability  # noqa: S311

    async def count_thread_depth(self, post_id: uuid.UUID) -> int:
        """@brief Number of Sassybot comments on the post (max ``MAX_THREAD_COMMENTS``)."""
        return await self._repo.count_bot_comments(post_id, self._bot_id)
