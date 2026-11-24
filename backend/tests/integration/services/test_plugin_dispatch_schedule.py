"""
@file test_plugin_dispatch_schedule.py
@brief Plugin dispatch is enqueued only after the request transaction commits.
"""

import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.plugins.events import schedule_plugin_dispatch

CID, PID = uuid.uuid4(), uuid.uuid4()


async def _run(commit: bool, delay: MagicMock) -> None:
    with patch("app.tasks.plugin_tasks.dispatch_plugin_event_task.apply_async", delay):
        engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
        async with AsyncSession(engine) as s:
            await s.execute(text("select 1"))
            schedule_plugin_dispatch(s, CID, PID, None)
            delay.assert_not_called()  # nothing before commit
            await (s.commit() if commit else s.rollback())
        await engine.dispose()


async def test_enqueued_after_commit():
    delay = MagicMock()
    await _run(True, delay)
    delay.assert_called_once_with(args=(str(CID), str(PID), ""), countdown=1, retry=False)


async def test_rollback_never_dispatches():
    delay = MagicMock()
    await _run(False, delay)
    delay.assert_not_called()


async def test_enqueue_error_does_not_break_commit():
    delay = MagicMock(side_effect=RuntimeError("broker down"))
    await _run(True, delay)  # must not raise


async def test_savepoint_rollback_keeps_pending_dispatch():
    delay = MagicMock()
    with patch("app.tasks.plugin_tasks.dispatch_plugin_event_task.apply_async", delay):
        engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
        async with AsyncSession(engine) as s:
            await s.execute(text("select 1"))
            schedule_plugin_dispatch(s, CID, PID, None)
            nested = await s.begin_nested()
            await nested.rollback()
            await s.commit()
        await engine.dispose()
    delay.assert_called_once()
