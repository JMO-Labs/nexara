"""
@file test_sassybot_runner.py
@brief Unit tests for the Sassybot pipeline gating and authorship.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.community import Community
from app.models.post import Comment
from app.repositories.comment_repo import CommentRepository
from app.repositories.sassybot_repo import SassybotRepository
from app.services.ai.provider import AIBudgetExhaustedError, AIError
from app.services.ai.sassybot_runner import run_sassybot
from app.services.ai.sassybot_service import SassybotService

CID = uuid.uuid4()
PID = uuid.uuid4()
BOT = uuid.uuid4()


async def _run(*, enabled=True, trigger=True, depth=0, force=False, gen="hi", exc=None):
    repo = AsyncMock(spec=SassybotRepository)
    community = MagicMock(spec=Community)
    community.sassybot_enabled = enabled
    repo.get_community.return_value = community
    repo.get_post_and_author.return_value = None
    svc = AsyncMock(spec=SassybotService)
    svc.should_trigger.return_value = trigger
    svc.count_thread_depth.return_value = depth
    svc.generate_comment.return_value = gen
    svc.generate_comment.side_effect = exc
    comments = AsyncMock(spec=CommentRepository)
    comments.create_comment.return_value = MagicMock(spec=Comment)
    ok = await run_sassybot(
        PID, CID, force=force, service=svc, repo=repo, comment_repo=comments,
        bot_user_id=BOT, event_bus=None,
    )  # fmt: skip
    return ok, svc, comments


async def test_creates_comment_as_bot() -> None:
    ok, _, comments = await _run()
    assert ok
    kw = comments.create_comment.call_args.kwargs
    assert kw["author_id"] == BOT and kw["content"] == "hi" and kw["post_id"] == PID


async def test_disabled_skips() -> None:
    ok, svc, _ = await _run(enabled=False)
    assert not ok
    svc.generate_comment.assert_not_called()


async def test_probability_gate_skips() -> None:
    ok, _, comments = await _run(trigger=False)
    assert not ok
    comments.create_comment.assert_not_called()


async def test_force_bypasses_gate() -> None:
    ok, svc, _ = await _run(trigger=False, force=True)
    assert ok
    svc.should_trigger.assert_not_called()


async def test_depth_limit_skips_even_when_forced() -> None:
    ok, _, comments = await _run(depth=3, force=True)
    assert not ok
    comments.create_comment.assert_not_called()


async def test_ai_errors_skipped() -> None:
    assert not (await _run(exc=AIError("x")))[0]
    assert not (await _run(exc=AIBudgetExhaustedError("x")))[0]


async def test_empty_text_skips_comment() -> None:
    ok, _, comments = await _run(gen=None)
    assert not ok
    comments.create_comment.assert_not_called()


async def test_emits_comment_created_to_audience(monkeypatch) -> None:
    from datetime import UTC, datetime

    from app.services.ai import sassybot_runner as mod

    repo = AsyncMock(spec=SassybotRepository)
    community = MagicMock(spec=Community)
    community.sassybot_enabled = True
    repo.get_community.return_value = community
    post = MagicMock(visibility="community", subgroup_id=None, author_id=uuid.uuid4())
    repo.get_post_and_author.return_value = (post, MagicMock(), True)
    svc = AsyncMock(spec=SassybotService)
    svc.count_thread_depth.return_value = 0
    svc.generate_comment.return_value = "hi"
    comment = MagicMock(spec=Comment)
    comment.id = uuid.uuid4()
    comment.content = "hi"
    comment.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    comments = AsyncMock(spec=CommentRepository)
    comments.create_comment.return_value = comment
    audience = [uuid.uuid4()]
    resolve = AsyncMock(return_value=audience)
    emit = AsyncMock()
    monkeypatch.setattr(mod, "resolve_audience", resolve)
    monkeypatch.setattr(mod, "emit_to_audience", emit)
    bus = MagicMock()

    ok = await run_sassybot(
        PID, CID, force=True, service=svc, repo=repo, comment_repo=comments,
        bot_user_id=BOT, event_bus=bus,
    )  # fmt: skip

    assert ok
    assert resolve.await_args.kwargs["author_id"] == post.author_id
    args = emit.await_args.args
    assert args[0] is bus and args[1] == audience
    assert args[3]["comment"]["author"]["username"] == "sassybot"
    assert args[3]["post_id"] == str(PID)
