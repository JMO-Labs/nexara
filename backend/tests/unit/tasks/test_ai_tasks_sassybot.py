"""
@file test_ai_tasks_sassybot.py
@brief Unit tests for the Sassybot Celery task and its async body.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tasks import ai_tasks

PID, CID, BOT = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _patch_common(monkeypatch, *, provider, bot_id: str):
    settings = MagicMock(SASSYBOT_USER_ID=bot_id)
    monkeypatch.setattr(ai_tasks, "get_settings", lambda: settings)
    monkeypatch.setattr(ai_tasks, "get_ai_provider", lambda s: provider)
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = session
    monkeypatch.setattr(ai_tasks, "async_session_factory", factory)
    monkeypatch.setattr(ai_tasks, "get_storage_backend", lambda s: MagicMock())
    return session


async def test_no_provider_returns_false(monkeypatch) -> None:
    session = _patch_common(monkeypatch, provider=None, bot_id=str(BOT))
    assert await ai_tasks._sassybot_async(PID, CID, False) is False
    session.commit.assert_not_awaited()


async def test_no_bot_user_returns_false(monkeypatch) -> None:
    _patch_common(monkeypatch, provider=MagicMock(), bot_id="")
    assert await ai_tasks._sassybot_async(PID, CID, False) is False


@pytest.mark.parametrize("created", [True, False])
async def test_runs_pipeline_and_commits(monkeypatch, created: bool) -> None:
    session = _patch_common(monkeypatch, provider=MagicMock(), bot_id=str(BOT))
    run = AsyncMock(return_value=created)
    monkeypatch.setattr("app.services.ai.sassybot_runner.run_sassybot", run)
    assert await ai_tasks._sassybot_async(PID, CID, True) is created
    kw = run.await_args.kwargs
    assert kw["force"] is True and kw["bot_user_id"] == BOT
    session.commit.assert_awaited_once()


def test_task_entry_runs_async(monkeypatch) -> None:
    seen = {}

    async def fake(post_id, community_id, force):
        seen.update(p=post_id, c=community_id, f=force)
        return True

    monkeypatch.setattr(ai_tasks, "_sassybot_async", fake)
    assert ai_tasks.sassybot_comment_task(str(PID), str(CID), True) == {"created": True}
    assert seen == {"p": PID, "c": CID, "f": True}
