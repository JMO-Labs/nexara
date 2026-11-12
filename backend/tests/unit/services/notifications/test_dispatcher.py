"""@file Tests for the notification Dispatcher."""

import asyncio
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.notifications.dispatcher import Dispatcher
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
    assert set(_d()._channels) == {"inapp", "email", "push"}


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
