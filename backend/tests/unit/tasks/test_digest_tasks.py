"""@file Tests for digest_dispatch and send_digest_email tasks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.tasks import notification_tasks as nt


def _session_cm(session):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


async def test_dispatch_drains_due_types_and_spawns():
    uid, nid = uuid4(), uuid4()
    session = MagicMock()
    session.commit = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uid])
    repo.list_pending_types = AsyncMock(return_value=["comment", "mention"])
    repo.drain = AsyncMock(return_value=[nid])
    st = MagicMock(
        digest_cadence={"comment": "hourly", "mention": "instant"},
        digest_last_sent_at=None,
        dnd_timezone="UTC",
    )
    srepo = MagicMock()
    srepo.get_by_user_id = AsyncMock(return_value=st)
    with (
        patch.object(nt, "async_session_factory", return_value=_session_cm(session)),
        patch.object(nt, "DigestRepository", return_value=repo),
        patch.object(nt, "SettingsRepository", return_value=srepo),
        patch.object(nt.send_digest_email, "delay") as delay,
    ):
        n = await nt._digest_dispatch_async(datetime(2026, 11, 13, 12, tzinfo=UTC))
    assert n == 2  # instant rows are due too
    delay.assert_any_call(str(uid), "comment", [str(nid)])
    delay.assert_any_call(str(uid), "mention", [str(nid)])
    assert st.digest_last_sent_at is not None


async def test_dispatch_skips_user_without_settings():
    session = MagicMock()
    session.commit = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uuid4()])
    srepo = MagicMock()
    srepo.get_by_user_id = AsyncMock(return_value=None)
    with (
        patch.object(nt, "async_session_factory", return_value=_session_cm(session)),
        patch.object(nt, "DigestRepository", return_value=repo),
        patch.object(nt, "SettingsRepository", return_value=srepo),
    ):
        assert await nt._digest_dispatch_async(datetime.now(UTC)) == 0


async def test_send_digest_missing_user_skipped():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    with patch.object(nt, "async_session_factory", return_value=_session_cm(session)):
        out = await nt._send_digest_email_async(uuid4(), "comment", [uuid4()])
    assert out == {"status": "skipped"}


async def test_send_digest_renders_and_sends():
    user = MagicMock(email="a@b.c", community_id=uuid4())
    notes = [MagicMock(payload={"message": "hi", "link": "/x"})]
    res = MagicMock()
    res.scalars.return_value.all.return_value = notes
    session = MagicMock()
    session.get = AsyncMock(return_value=user)
    session.execute = AsyncMock(return_value=res)
    sender = MagicMock()
    sender.send = AsyncMock(return_value=True)
    with (
        patch.object(nt, "async_session_factory", return_value=_session_cm(session)),
        patch.object(nt, "BrandingRepository") as br,
        patch.object(nt, "EmailSender", return_value=sender),
    ):
        br.return_value.get = AsyncMock(return_value=None)
        out = await nt._send_digest_email_async(uuid4(), "comment", [uuid4()])
    assert out == {"status": "sent"}
    assert "hi" in sender.send.await_args.kwargs["html_body"]


async def test_send_digest_no_notifications_skipped():
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.get = AsyncMock(return_value=MagicMock(email="a@b.c", community_id=uuid4()))
    session.execute = AsyncMock(return_value=res)
    with patch.object(nt, "async_session_factory", return_value=_session_cm(session)):
        assert await nt._send_digest_email_async(uuid4(), "c", [uuid4()]) == {"status": "skipped"}


def _dispatch_patches(session, repo, st):
    srepo = MagicMock()
    srepo.get_by_user_id = AsyncMock(return_value=st)
    return (
        patch.object(nt, "async_session_factory", return_value=_session_cm(session)),
        patch.object(nt, "DigestRepository", return_value=repo),
        patch.object(nt, "SettingsRepository", return_value=srepo),
    )


async def test_dispatch_commits_before_delay():
    uid, nid = uuid4(), uuid4()
    order = MagicMock()
    session = MagicMock()
    session.commit = order.commit
    order.commit.side_effect = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uid])
    repo.list_pending_types = AsyncMock(return_value=["comment"])
    repo.drain = AsyncMock(return_value=[nid])
    st = MagicMock(
        digest_cadence={"comment": "hourly"}, digest_last_sent_at=None, dnd_timezone="UTC"
    )
    p1, p2, p3 = _dispatch_patches(session, repo, st)
    with p1, p2, p3, patch.object(nt.send_digest_email, "delay", order.delay):
        await nt._digest_dispatch_async(datetime(2026, 11, 13, 12, tzinfo=UTC))
    names = [c[0] for c in order.mock_calls if c[0] in ("commit", "delay")]
    assert names == ["commit", "delay"]


async def test_dispatch_off_cadence_drains_and_drops():
    uid, nid = uuid4(), uuid4()
    session = MagicMock()
    session.commit = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uid])
    repo.list_pending_types = AsyncMock(return_value=["comment"])
    repo.drain = AsyncMock(return_value=[nid])
    st = MagicMock(digest_cadence={"comment": "off"}, digest_last_sent_at=None, dnd_timezone="UTC")
    p1, p2, p3 = _dispatch_patches(session, repo, st)
    with p1, p2, p3, patch.object(nt.send_digest_email, "delay") as delay:
        n = await nt._digest_dispatch_async(datetime(2026, 11, 13, 12, tzinfo=UTC))
    assert n == 0
    repo.drain.assert_awaited_once_with(uid, "comment")
    delay.assert_not_called()
    session.commit.assert_awaited_once()


async def test_dispatch_instant_cadence_sends():
    uid, nid = uuid4(), uuid4()
    session = MagicMock()
    session.commit = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uid])
    repo.list_pending_types = AsyncMock(return_value=["comment"])
    repo.drain = AsyncMock(return_value=[nid])
    st = MagicMock(
        digest_cadence={"comment": "instant"}, digest_last_sent_at=None, dnd_timezone="UTC"
    )
    p1, p2, p3 = _dispatch_patches(session, repo, st)
    with p1, p2, p3, patch.object(nt.send_digest_email, "delay") as delay:
        n = await nt._digest_dispatch_async(datetime(2026, 11, 13, 12, tzinfo=UTC))
    assert n == 1
    delay.assert_called_once_with(str(uid), "comment", [str(nid)])


async def test_dispatch_not_due_type_is_left_queued():
    uid = uuid4()
    session = MagicMock()
    session.commit = AsyncMock()
    repo = MagicMock()
    repo.list_users_with_pending = AsyncMock(return_value=[uid])
    repo.list_pending_types = AsyncMock(return_value=["comment"])
    repo.drain = AsyncMock()
    st = MagicMock(
        digest_cadence={"comment": "hourly"},
        digest_last_sent_at=datetime(2026, 11, 13, 11, 59, tzinfo=UTC),
        dnd_timezone="UTC",
    )
    p1, p2, p3 = _dispatch_patches(session, repo, st)
    with p1, p2, p3, patch.object(nt.send_digest_email, "delay") as delay:
        n = await nt._digest_dispatch_async(datetime(2026, 11, 13, 12, tzinfo=UTC))
    assert n == 0
    repo.drain.assert_not_awaited()
    delay.assert_not_called()


def test_digest_dispatch_task_runs_async_impl():
    with patch.object(nt, "_digest_dispatch_async", new=AsyncMock(return_value=3)) as impl:
        assert nt.digest_dispatch() == 3
    impl.assert_awaited_once()


def test_send_digest_email_invalid_uuid_returns_error():
    assert nt.send_digest_email("nope", "comment", []) == {"status": "error"}
    assert nt.send_digest_email(str(uuid4()), "comment", ["bad"]) == {"status": "error"}


def test_send_digest_email_runs_async_impl():
    with patch.object(
        nt, "_send_digest_email_async", new=AsyncMock(return_value={"status": "sent"})
    ):
        out = nt.send_digest_email(str(uuid4()), "comment", [str(uuid4())])
    assert out == {"status": "sent"}


def test_send_digest_email_retries_on_failure():
    boom = RuntimeError("smtp down")
    with (
        patch.object(nt, "_send_digest_email_async", new=AsyncMock(side_effect=boom)),
        patch.object(nt.send_digest_email, "retry", side_effect=Exception("retry")) as retry,
        pytest.raises(Exception, match="retry"),
    ):
        nt.send_digest_email.run(str(uuid4()), "comment", [str(uuid4())])
    retry.assert_called_once_with(exc=boom)
