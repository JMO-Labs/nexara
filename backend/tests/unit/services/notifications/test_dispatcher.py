"""@file Tests for the notification Dispatcher."""

import asyncio
from datetime import UTC, datetime
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.dispatcher import Dispatcher
from app.services.notifications.dnd import gate_channels
from app.services.realtime.event_bus import EventBus


class _Fake:
    def __init__(self, key: str, result: object = None, delay: float = 0) -> None:
        self.key: ClassVar[str] = key  # type: ignore[misc]
        self.calls = 0
        self._result = result if result is not None else ChannelResult(ok=True)
        self._delay = delay

    async def send(self, notification: Notification) -> ChannelResult:
        self.calls += 1
        await asyncio.sleep(self._delay)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result  # type: ignore[return-value]


def _d() -> Dispatcher:
    return Dispatcher(AsyncMock(spec=EventBus))


_N = MagicMock(spec=Notification)
_T = MagicMock()
_T.key = "mention"


def test_registers_builtin_channels() -> None:
    assert set(_d()._channels) == {"inapp", "email", "push", "apprise"}


async def test_fanout_only_enabled_channels() -> None:
    d = _d()
    a, b = _Fake("inapp"), _Fake("email")
    d.register_channel(a)  # type: ignore[arg-type]
    d.register_channel(b)  # type: ignore[arg-type]
    res = await d.dispatch(_N, _T, {"inapp": True, "email": False})
    assert (a.calls, b.calls) == (1, 0)
    assert len(res) == 1 and res[0].ok


async def test_unknown_channel_ignored() -> None:
    assert await _d().dispatch(_N, _T, {"webhook": True}) == []


async def test_failure_isolated_and_not_propagated() -> None:
    d = _d()
    d.register_channel(_Fake("inapp", RuntimeError("boom")))  # type: ignore[arg-type]
    ok = _Fake("email")
    d.register_channel(ok)  # type: ignore[arg-type]
    res = await d.dispatch(_N, _T, {"inapp": True, "email": True})
    assert ok.calls == 1
    assert res[0].ok is False and res[0].error == "boom"
    assert res[1].ok


async def test_sends_run_in_parallel() -> None:
    d = _d()
    d.register_channel(_Fake("inapp", delay=0.2))  # type: ignore[arg-type]
    d.register_channel(_Fake("email", delay=0.2))  # type: ignore[arg-type]
    loop = asyncio.get_running_loop()
    start = loop.time()
    await d.dispatch(_N, _T, {"inapp": True, "email": True})
    assert loop.time() - start < 0.35


async def test_fcm_gated_by_push_preference() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from app.services.notifications.channels.base import ChannelResult
    from app.services.notifications.dispatcher import Dispatcher

    d = Dispatcher(MagicMock())
    fcm = MagicMock()
    fcm.key = "fcm"
    fcm.send = AsyncMock(return_value=ChannelResult(ok=True))
    d.register_channel(fcm)
    await d.dispatch(MagicMock(), MagicMock(key="t"), {"push": False})
    fcm.send.assert_not_called()
    await d.dispatch(MagicMock(), MagicMock(key="t"), {"push": True})
    fcm.send.assert_awaited_once()


def test_registers_optional_fcm_channel() -> None:
    fcm = _Fake("fcm")
    d = Dispatcher(AsyncMock(spec=EventBus), fcm=fcm)  # type: ignore[arg-type]
    assert d._channels["fcm"] is fcm


def _inapp_dispatcher() -> tuple[Dispatcher, AsyncMock]:
    bus = AsyncMock(spec=EventBus)
    return Dispatcher(bus), bus


def _real_notif() -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id, n.user_id, n.type, n.payload = uuid4(), uuid4(), "mention", {}
    n.created_at, n.updated_at, n.count, n.actor_ids = datetime.now(UTC), None, 1, []
    return n


async def test_inapp_os_notify_false_when_push_suppressed() -> None:
    """DnD/snooze/per-type gating that turns push off must also stop OS notifications."""
    d, bus = _inapp_dispatcher()
    t = MagicMock()
    t.key, t.bypass_dnd = "mention", False
    eff = gate_channels({"inapp": True, "push": True}, t, in_dnd_now=True)
    await d.dispatch(_real_notif(), t, eff)  # type: ignore[arg-type]
    assert bus.emit.await_args.args[0].payload["os_notify"] is False


async def test_inapp_os_notify_true_when_push_on() -> None:
    d, bus = _inapp_dispatcher()
    with patch(
        "app.services.notifications.channels.push.PushChannel.send",
        AsyncMock(return_value=ChannelResult(ok=True)),
    ):
        await d.dispatch(_real_notif(), _T, {"inapp": True, "push": True})
    assert bus.emit.await_args.args[0].payload["os_notify"] is True
