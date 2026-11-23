"""
@file test_notification_reply_to.py
@brief Only comment/mention/new_post emails get a Reply-To, and only when active.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.notification_tasks import _reply_to

POST = str(uuid.uuid4())


def _community(on=True, host="imap.example.com"):
    return SimpleNamespace(
        features={"reply_by_email": on},
        inbound_imap_host=host,
        inbound_imap_user="bot",
        inbound_imap_password="enc",
        inbound_reply_address="reply@example.com",
    )


async def _run(ntype, community, payload=None):
    user = SimpleNamespace(id=uuid.uuid4(), community_id=uuid.uuid4())
    session = MagicMock(commit=AsyncMock())
    tokens = MagicMock(create=AsyncMock(return_value="TOKEN"))
    with (
        patch("app.repositories.community_repo.CommunityRepository") as cr,
        patch("app.repositories.reply_token_repo.ReplyTokenRepository", return_value=tokens),
    ):
        cr.return_value.get = AsyncMock(return_value=community)
        out = await _reply_to(session, user, ntype, payload or {"post_id": POST})
    return out, tokens, user


async def test_comment_mention_new_post_get_fresh_token():
    for ntype in ("comment", "mention", "new_post"):
        out, tokens, user = await _run(ntype, _community())
        assert out == "reply+TOKEN@example.com"
        tokens.create.assert_awaited_once_with(user.community_id, user.id, uuid.UUID(POST))


async def test_other_types_feature_off_incomplete_or_no_post_get_none():
    assert (await _run("event_reminder", _community()))[0] is None
    assert (await _run("comment", _community(on=False)))[0] is None
    assert (await _run("comment", _community(host=None)))[0] is None
    assert (await _run("comment", _community(), {"x": 1}))[0] is None
    out, tokens, _ = await _run("comment", None)
    assert out is None
    tokens.create.assert_not_awaited()
