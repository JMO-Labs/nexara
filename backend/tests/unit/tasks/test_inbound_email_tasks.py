"""
@file test_inbound_email_tasks.py
@brief inbound_email.poll gating, message handling and delete-after-process.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import inbound_email_tasks as t


def _community(on=True):
    return SimpleNamespace(
        features={"reply_by_email": on},
        inbound_imap_host="imap.example.com",
        inbound_imap_port=993,
        inbound_imap_user="bot",
        inbound_imap_password="enc",
        inbound_reply_address="reply@example.com",
        inbound_authserv_id="mx.example.com",
    )


def _patches(community, process="posted"):
    sess = MagicMock()
    sess.__aenter__ = AsyncMock(return_value=sess)
    sess.__aexit__ = AsyncMock(return_value=None)
    sess.commit = AsyncMock()
    sess.rollback = AsyncMock()
    repo = MagicMock()
    repo.return_value.get = AsyncMock(return_value=community)
    svc = MagicMock()
    svc.return_value.process = AsyncMock(side_effect=process if callable(process) else None)
    if not callable(process):
        svc.return_value.process.return_value = process
    return sess, repo, svc


async def test_feature_off_never_connects():
    sess, repo, _ = _patches(_community(on=False))
    with (
        patch.object(t, "async_session_factory", return_value=sess),
        patch.object(t, "CommunityRepository", repo),
        patch.object(t.imap_client, "fetch_unseen") as fetch,
    ):
        assert await t._poll_async() == {"posted": 0, "ignored": 0}
    fetch.assert_not_called()


async def test_poll_processes_and_deletes_all_messages():
    sess, repo, svc = _patches(_community())
    conn = object()
    raw = b"From: a@b.com\nTo: reply+x@example.com\n\nhi"
    with (
        patch.object(t, "async_session_factory", return_value=sess),
        patch.object(t, "CommunityRepository", repo),
        patch.object(t, "ReplyTokenRepository", return_value=MagicMock(purge=AsyncMock())),
        patch.object(t, "decrypt_secret", return_value="pw"),
        patch.object(t, "InboundService", svc),
        patch("app.api.v1.posts._build_service"),
        patch.object(
            t.imap_client, "fetch_unseen", return_value=(conn, [(b"1", raw), (b"2", raw)])
        ),
        patch.object(t.imap_client, "finish") as fin,
    ):
        assert await t._poll_async() == {"posted": 2, "ignored": 0}
    fin.assert_called_once_with(conn, [b"1", b"2"])


async def test_processing_error_counts_ignored_and_still_deletes():
    sess, repo, svc = _patches(_community(), process=MagicMock(side_effect=RuntimeError("boom")))
    with (
        patch.object(t, "async_session_factory", return_value=sess),
        patch.object(t, "CommunityRepository", repo),
        patch.object(t, "ReplyTokenRepository", return_value=MagicMock(purge=AsyncMock())),
        patch.object(t, "decrypt_secret", return_value="pw"),
        patch.object(t, "InboundService", svc),
        patch("app.api.v1.posts._build_service"),
        patch.object(t.imap_client, "fetch_unseen", return_value=(object(), [(b"1", b"x")])),
        patch.object(t.imap_client, "finish") as fin,
    ):
        assert await t._poll_async() == {"posted": 0, "ignored": 1}
    fin.assert_called_once()


async def test_network_error_is_logged_not_raised():
    sess, repo, _ = _patches(_community())
    with (
        patch.object(t, "async_session_factory", return_value=sess),
        patch.object(t, "CommunityRepository", repo),
        patch.object(t, "ReplyTokenRepository", return_value=MagicMock(purge=AsyncMock())),
        patch.object(t, "decrypt_secret", return_value="pw"),
        patch.object(t.imap_client, "fetch_unseen", side_effect=OSError("down")),
    ):
        assert await t._poll_async() == {"posted": 0, "ignored": 0}
