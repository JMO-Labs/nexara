"""
@file test_recap_tasks.py
@brief Unit tests: recap dispatch enqueues once per due id; empty recap sends nothing.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.tasks import recap_tasks


def test_dispatch_enqueues_each_due_user_once():
    a, b = uuid.uuid4(), uuid.uuid4()
    with (
        patch.object(recap_tasks, "_dispatch_async", new=AsyncMock(return_value=[a, b])),
        patch.object(recap_tasks.send_recap_email, "delay") as delay,
    ):
        assert recap_tasks.recap_dispatch() == 2
    assert [c.args[0] for c in delay.call_args_list] == [str(a), str(b)]


def test_dispatch_twice_same_hour_enqueues_once():
    uid = uuid.uuid4()
    results = iter([[uid], []])
    with (
        patch.object(
            recap_tasks, "_dispatch_async", new=AsyncMock(side_effect=lambda _n: next(results))
        ),
        patch.object(recap_tasks.send_recap_email, "delay") as delay,
    ):
        recap_tasks.recap_dispatch()
        recap_tasks.recap_dispatch()
    delay.assert_called_once_with(str(uid))


def _session_cm(user):
    session = MagicMock()
    session.get = AsyncMock(return_value=user)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


async def test_empty_recap_sends_no_email():
    user = MagicMock(spec=User)
    user.deleted_at = None
    user.is_active = True
    with (
        patch.object(recap_tasks, "async_session_factory", return_value=_session_cm(user)),
        patch.object(recap_tasks, "RecapService") as svc,
        patch.object(recap_tasks, "EmailSender") as sender,
    ):
        svc.return_value.build = AsyncMock(return_value=[])
        out = await recap_tasks._send_async(uuid.uuid4())
    assert out == {"status": "skipped"}
    sender.assert_not_called()


async def test_send_includes_unsubscribe_header_and_absolute_links():
    user = MagicMock(spec=User)
    user.deleted_at = None
    user.is_active = True
    user.email = "m@example.com"
    user.community_id = uuid.uuid4()
    section = {"key": "k", "title": "On this day", "items": [{"text": "hi", "link": "/app/post/1"}]}
    with (
        patch.object(recap_tasks, "async_session_factory", return_value=_session_cm(user)),
        patch.object(recap_tasks, "RecapService") as svc,
        patch.object(recap_tasks, "BrandingRepository") as br,
        patch.object(recap_tasks, "EmailSender") as sender,
    ):
        svc.return_value.build = AsyncMock(return_value=[section])
        br.return_value.get = AsyncMock(return_value=None)
        sender.return_value.send = AsyncMock(return_value=True)
        out = await recap_tasks._send_async(uuid.uuid4())
    kw = sender.return_value.send.await_args.kwargs
    assert out == {"status": "sent"}
    assert (
        kw["list_unsubscribe"].startswith("<http")
        and "recap/unsubscribe?token=" in kw["list_unsubscribe"]
    )
    assert 'href="http' in kw["html_body"] and "<h1" in kw["html_body"] and "<h2" in kw["html_body"]
