"""
@file test_prompt_tasks.py
@brief Unit tests for prompt Celery tasks wiring (media attacher, commit).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks import prompt_tasks


def _factory(session):
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


@pytest.mark.parametrize(
    ("runner", "method", "key"),
    [
        (prompt_tasks._fire_prompts_async, "fire_due_prompts", "fired"),
        (prompt_tasks._generate_summaries_async, "finalise_expired", "finalised"),
    ],
)
async def test_runner_wires_media_attacher_and_commits(runner, method, key):
    session = AsyncMock()
    svc_cls = MagicMock()
    setattr(svc_cls.return_value, method, AsyncMock(return_value=3))
    with (
        patch.object(prompt_tasks, "async_session_factory", _factory(session)),
        patch.object(prompt_tasks, "_community_id", return_value=uuid.uuid4()),
        patch.object(prompt_tasks, "PromptService", svc_cls),
        patch.object(prompt_tasks, "NotificationService"),
        patch.object(prompt_tasks, "MediaRepository") as media_cls,
    ):
        result = await runner()
    assert result == {key: 3}
    media_cls.assert_called_once_with(session)
    attacher = svc_cls.call_args.kwargs["media_attacher"]
    assert attacher is media_cls.return_value.attach_to_post
    session.commit.assert_awaited_once()


def test_beat_entries_run_async():
    with patch.object(prompt_tasks, "_fire_prompts_async", AsyncMock(return_value={"fired": 1})):
        assert prompt_tasks.fire_prompts() == {"fired": 1}
    with patch.object(
        prompt_tasks, "_generate_summaries_async", AsyncMock(return_value={"finalised": 2})
    ):
        assert prompt_tasks.generate_summaries() == {"finalised": 2}


def test_seed_builtin_prompts_missing_file_returns_zero():
    with patch("pathlib.Path.exists", return_value=False):
        assert prompt_tasks.seed_builtin_prompts() == {"inserted": 0}


def test_seed_builtin_prompts_loads_json_and_runs_async():
    seed = AsyncMock(return_value={"inserted": 5})
    with patch.object(prompt_tasks, "_seed_builtin_prompts_async", seed):
        assert prompt_tasks.seed_builtin_prompts() == {"inserted": 5}
    data = seed.await_args.args[0]
    assert isinstance(data, list) and data


async def test_seed_async_skips_existing_and_inserts_new():
    session = AsyncMock()
    session.add = MagicMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = object()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[existing, missing])
    entries = [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]
    with (
        patch.object(prompt_tasks, "async_session_factory", _factory(session)),
        patch.object(prompt_tasks, "_community_id", return_value=uuid.uuid4()),
        patch("app.models.prompt.Prompt") as prompt_cls,
    ):
        result = await prompt_tasks._seed_builtin_prompts_async(entries)
    assert result == {"inserted": 1}
    session.add.assert_called_once_with(prompt_cls.return_value)
    assert prompt_cls.call_args.kwargs["title"] == "B"
    assert "id" not in prompt_cls.call_args.kwargs
    session.commit.assert_awaited_once()
