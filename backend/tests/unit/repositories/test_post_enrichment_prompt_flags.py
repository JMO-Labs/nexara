"""
@file test_post_enrichment_prompt_flags.py
@brief Unit tests: enriched posts expose prompt flags (nexara#252).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.post import Post
from app.models.user import User
from app.repositories.post_enrichment import enrich_posts

POST_ID = uuid.uuid4()


def _session_for(post: MagicMock) -> AsyncMock:
    """@brief Build a session returning one post row and empty side tables."""
    user = MagicMock(spec=User)
    user.id, user.username, user.display_name, user.avatar_url = (
        uuid.uuid4(),
        "alice",
        "Alice",
        None,
    )
    posts = MagicMock()
    posts.all.return_value = [(post, user)]
    empty = MagicMock()
    empty.all.return_value = []
    comments = MagicMock()
    comments.all.return_value = []
    polls = MagicMock()
    polls.scalars.return_value.all.return_value = []
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[posts, empty, empty, comments, polls])
    return session


def _post(**flags: object) -> MagicMock:
    """@brief Build a Post mock with the given prompt flag values."""
    post = MagicMock(spec=Post)
    post.id, post.content, post.subgroup_id = POST_ID, "hi", None
    post.created_at = post.updated_at = datetime.now(UTC)
    post.is_prompt_post = flags.get("is_prompt_post", False)
    post.is_prompt_summary = flags.get("is_prompt_summary", False)
    post.reply_to_prompt_id = flags.get("reply_to_prompt_id")
    post.source_prompt_post_id = flags.get("source_prompt_post_id")
    return post


async def test_enriched_post_has_prompt_flag_defaults() -> None:
    """Plain posts expose false/null prompt flags."""
    out = await enrich_posts(_session_for(_post()), [POST_ID], None)
    item = out[POST_ID]
    assert item["is_prompt_post"] is False
    assert item["is_prompt_summary"] is False
    assert item["reply_to_prompt_id"] is None
    assert item["source_prompt_post_id"] is None


async def test_enriched_post_has_prompt_flag_values() -> None:
    """Prompt-related posts expose their flags and ids as strings."""
    reply_id, source_id = uuid.uuid4(), uuid.uuid4()
    post = _post(
        is_prompt_post=True,
        is_prompt_summary=True,
        reply_to_prompt_id=reply_id,
        source_prompt_post_id=source_id,
    )
    item = (await enrich_posts(_session_for(post), [POST_ID], None))[POST_ID]
    assert item["is_prompt_post"] is True
    assert item["is_prompt_summary"] is True
    assert item["reply_to_prompt_id"] == str(reply_id)
    assert item["source_prompt_post_id"] == str(source_id)
