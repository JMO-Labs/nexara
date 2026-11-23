"""
@file test_inbound_service.py
@brief InboundService: every re-check before an emailed reply becomes a comment.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.services.email.inbound_service import RATE_LIMIT, InboundService

CID = uuid.uuid4()
TOKEN = "T" * 24


def _msg(body="Thanks!", sender="ruth@example.com", **headers) -> EmailMessage:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = f"reply+{TOKEN}@mail.example.com"
    for k, v in headers.items():
        m[k.replace("_", "-")] = v
    m.set_content(body)
    return m


def _svc(**over):
    user = over.pop("user", None) or SimpleNamespace(
        id=uuid.uuid4(),
        email="Ruth@Example.com",
        is_active=True,
        deleted_at=None,
        memorialized_at=None,
    )
    post = SimpleNamespace(id=uuid.uuid4(), author_id=uuid.uuid4())
    row = over.pop("row", None) or SimpleNamespace(
        community_id=CID,
        user_id=user.id,
        post_id=post.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    community = SimpleNamespace(
        features={"reply_by_email": True}, inbound_reply_address="reply@mail.example.com"
    )
    communities, tokens, moderation, posts, ps, session = (AsyncMock() for _ in range(6))
    communities.get.return_value = over.pop("community", community)
    tokens.get.return_value = row
    tokens.count_replies_since.return_value = over.pop("recent", 0)
    moderation.is_blocked_either.return_value = over.pop("blocked", False)
    posts.get_by_id.return_value = over.pop("post", post)
    session.get.return_value = user
    for k, v in over.items():
        ps.add_comment.side_effect = v
    svc = InboundService(tokens, communities, moderation, posts, ps, session, CID)
    return svc, ps, tokens, user, row


async def test_valid_reply_posts_comment_on_token_post_only():
    svc, ps, tokens, user, row = _svc()
    assert await svc.process(_msg()) == "posted"
    ps.add_comment.assert_awaited_once_with(row.post_id, user, "Thanks!")
    tokens.log_reply.assert_awaited_once_with(user.id)


@pytest.mark.parametrize(
    "headers",
    [{"Auto_Submitted": "auto-replied"}, {"Precedence": "bulk"}],
)
async def test_auto_replies_ignored(headers):
    svc, ps, *_ = _svc()
    assert await svc.process(_msg(**headers)) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_expired_token_ignored():
    row = SimpleNamespace(
        community_id=CID,
        user_id=uuid.uuid4(),
        post_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    svc, ps, *_ = _svc(row=row)
    assert await svc.process(_msg()) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_unknown_token_and_no_token_ignored():
    svc, ps, tokens, *_ = _svc()
    tokens.get.return_value = None
    assert await svc.process(_msg()) == "ignored"
    m = _msg()
    del m["To"]
    m["To"] = "someone@mail.example.com"
    assert await svc.process(m) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_sender_mismatch_ignored():
    svc, ps, *_ = _svc()
    assert await svc.process(_msg(sender="mallory@example.com")) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_sender_match_is_case_insensitive_after_parseaddr():
    svc, *_ = _svc()
    assert await svc.process(_msg(sender="Ruth R <RUTH@example.COM>")) == "posted"


@pytest.mark.parametrize(
    "flags",
    [
        {"is_active": False},
        {"memorialized_at": datetime.now(UTC)},
        {"deleted_at": datetime.now(UTC)},
    ],
)
async def test_inactive_memorialized_deleted_user_ignored(flags):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="ruth@example.com",
        **{"is_active": True, "deleted_at": None, "memorialized_at": None, **flags},
    )
    svc, ps, *_ = _svc(user=user)
    assert await svc.process(_msg()) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_blocked_by_post_author_ignored():
    svc, ps, *_ = _svc(blocked=True)
    assert await svc.process(_msg()) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_feature_off_or_unconfigured_ignored():
    svc, ps, *_ = _svc(community=SimpleNamespace(features={}, inbound_reply_address="r@x.org"))
    assert await svc.process(_msg()) == "ignored"
    svc, ps, *_ = _svc(
        community=SimpleNamespace(features={"reply_by_email": True}, inbound_reply_address=None)
    )
    assert await svc.process(_msg()) == "ignored"


async def test_missing_post_ignored_and_comment_service_denial_ignored():
    svc, ps, *_ = _svc(post=None)
    assert await svc.process(_msg()) == "ignored"
    svc, ps, tokens, *_ = _svc(add=NotFoundError("Post not found"))
    assert await svc.process(_msg()) == "ignored"
    tokens.log_reply.assert_not_awaited()


async def test_rate_limit_21st_reply_ignored():
    svc, ps, *_ = _svc(recent=RATE_LIMIT - 1)
    assert await svc.process(_msg()) == "posted"
    svc, ps, *_ = _svc(recent=RATE_LIMIT)
    assert await svc.process(_msg()) == "ignored"
    ps.add_comment.assert_not_awaited()


async def test_empty_after_cleaning_ignored():
    svc, ps, *_ = _svc()
    assert await svc.process(_msg("> only quoted\n")) == "ignored"
    ps.add_comment.assert_not_awaited()
