"""
@file test_chat_internals.py
@brief Coverage tests for ChatInternalsMixin broadcast/preview/rate-limit.
"""

from __future__ import annotations

import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import RateLimitError
from app.services.chat_helpers import CHAT_RATE_LIMIT_PER_MINUTE, channel_pubsub_name
from app.services.chat_internals import ChatInternalsMixin

COMMUNITY_ID = uuid.uuid4()


def _svc(**kw: object) -> ChatInternalsMixin:
    """@brief Build a mixin instance with mock collaborators."""
    s = ChatInternalsMixin()
    s._channel_repo = AsyncMock()  # type: ignore[assignment]
    s._community_id = COMMUNITY_ID
    s._rate_limiter = None
    s._broadcaster = None
    s._link_preview_enqueue = None
    for k, v in kw.items():
        setattr(s, k, v)
    return s


class TestBroadcast:
    """@brief _broadcast()."""

    async def test_default_publisher_and_legacy_topic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No broadcaster and no channel: default publish on legacy topic."""
        pub = AsyncMock(return_value=3)
        monkeypatch.setattr("app.services.realtime.pubsub.publish", pub)
        s = _svc()
        s._channel_repo.get.return_value = None  # type: ignore[attr-defined]
        cid = uuid.uuid4()
        assert await s._broadcast(cid, "t", {"a": 1}) == 3
        pub.assert_awaited_once_with(channel_pubsub_name(cid), {"type": "t", "payload": {"a": 1}})

    async def test_fans_out_to_members(self) -> None:
        """Resolved channel publishes per member."""
        pub = AsyncMock(return_value=1)
        s = _svc(_broadcaster=pub)
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        s._channel_repo.list_member_ids.return_value = [u1, u2]  # type: ignore[attr-defined]
        assert await s._broadcast(uuid.uuid4(), "t", {}, channel=MagicMock()) == 2
        assert [c.args[0] for c in pub.await_args_list] == [f"user:{u1}", f"user:{u2}"]


class TestEnqueueLinkPreviews:
    """@brief _enqueue_link_previews()."""

    async def test_no_urls_noop(self) -> None:
        """Content without URLs enqueues nothing."""
        enq = MagicMock()
        await _svc(_link_preview_enqueue=enq)._enqueue_link_previews("hello", uuid.uuid4())
        enq.assert_not_called()

    async def test_enqueue_failure_swallowed(self) -> None:
        """A failing enqueue is logged, not raised."""
        enq = MagicMock(side_effect=RuntimeError("boom"))
        await _svc(_link_preview_enqueue=enq)._enqueue_link_previews(
            "see https://example.com", uuid.uuid4()
        )
        enq.assert_called_once()

    async def test_default_task_delay_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without an injected enqueue the celery task's delay is used."""
        delay = MagicMock()
        mod = SimpleNamespace(scrape_link_preview=SimpleNamespace(delay=delay))
        monkeypatch.setitem(sys.modules, "app.tasks.link_preview_tasks", mod)
        mid = uuid.uuid4()
        await _svc()._enqueue_link_previews("https://example.com", mid)
        delay.assert_called_once()
        assert delay.call_args.kwargs["message_id"] == str(mid)

    async def test_task_import_failure_returns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unimportable task module is tolerated."""
        monkeypatch.setitem(sys.modules, "app.tasks.link_preview_tasks", None)
        await _svc()._enqueue_link_previews("https://example.com", uuid.uuid4())


class TestRateLimit:
    """@brief _enforce_rate_limit()."""

    async def test_no_limiter_passes(self) -> None:
        """No Valkey client means no limiting."""
        await _svc()._enforce_rate_limit(uuid.uuid4())

    async def test_first_hit_sets_expiry(self) -> None:
        """First INCR sets a 60s expiry."""
        r = AsyncMock()
        r.incr.return_value = 1
        await _svc(_rate_limiter=r)._enforce_rate_limit(uuid.uuid4())
        r.expire.assert_awaited_once()

    async def test_backend_error_fails_open(self) -> None:
        """Backend errors do not block sending."""
        r = AsyncMock()
        r.incr.side_effect = ConnectionError("down")
        await _svc(_rate_limiter=r)._enforce_rate_limit(uuid.uuid4())

    async def test_over_limit_raises(self) -> None:
        """Exceeding the per-minute cap raises RateLimitError."""
        r = AsyncMock()
        r.incr.return_value = CHAT_RATE_LIMIT_PER_MINUTE + 1
        with pytest.raises(RateLimitError):
            await _svc(_rate_limiter=r)._enforce_rate_limit(uuid.uuid4())
