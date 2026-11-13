"""@file Tests for digest_dispatch and send_digest_email tasks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
    assert n == 1
    repo.drain.assert_awaited_once_with(uid, "comment")
    delay.assert_called_once_with(str(uid), "comment", [str(nid)])
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
