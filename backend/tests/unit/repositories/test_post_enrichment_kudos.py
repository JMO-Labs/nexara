"""
@file test_post_enrichment_kudos.py
@brief Unit tests: enriched kudos posts expose recipient so the feed renders a kudos card.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.post import Post
from app.models.user import User
from app.repositories.post_enrichment import enrich_posts

POST_ID = uuid.uuid4()
RECIPIENT_ID = uuid.uuid4()


def _user(uid: uuid.UUID, name: str) -> MagicMock:
    """@brief Build a User mock."""
    user = MagicMock(spec=User)
    user.id, user.username, user.display_name, user.avatar_url = uid, name.lower(), name, None
    return user


def _result(rows: list[object]) -> MagicMock:
    """@brief Build an execute() result exposing rows via all()/scalars().all()."""
    res = MagicMock()
    res.all.return_value = rows
    res.scalars.return_value.all.return_value = rows
    return res


def _post(recipient_id: uuid.UUID | None) -> MagicMock:
    """@brief Build a Post mock with the given recipient."""
    post = MagicMock(spec=Post)
    post.id, post.content, post.subgroup_id = POST_ID, "Great job!", None
    post.created_at = post.updated_at = datetime.now(UTC)
    post.is_prompt_post = post.is_prompt_summary = False
    post.reply_to_prompt_id = post.source_prompt_post_id = None
    post.recipient_id = recipient_id
    return post


async def test_enriched_kudos_includes_recipient() -> None:
    """A kudos post carries recipient_id and a recipient summary."""
    post = _post(RECIPIENT_ID)
    rows = [
        _result([(post, _user(uuid.uuid4(), "Alice"))]),
        _result([_user(RECIPIENT_ID, "Richard")]),
        _result([]),
        _result([]),
        _result([]),
        _result([]),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=rows)
    item = (await enrich_posts(session, [POST_ID], None))[POST_ID]
    assert item["recipient_id"] == str(RECIPIENT_ID)
    assert item["recipient"]["display_name"] == "Richard"


async def test_enriched_plain_post_has_no_recipient() -> None:
    """Plain posts have null recipient fields."""
    rows = [_result([(_post(None), _user(uuid.uuid4(), "Alice"))])] + [_result([])] * 5
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=rows)
    item = (await enrich_posts(session, [POST_ID], None))[POST_ID]
    assert item["recipient_id"] is None
    assert item["recipient"] is None
