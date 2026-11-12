"""
@file test_sassybot_trigger.py
@brief PostService enqueues the Sassybot task on posts and @sassybot comments.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services.post_service import PostService


def _svc() -> PostService:
    return PostService(None, None, None, None, __import__("uuid").uuid4())  # type: ignore[arg-type]


def test_enqueue_unforced_for_plain_content(sassybot_delay) -> None:
    svc = _svc()
    pid = __import__("uuid").uuid4()
    svc._enqueue_sassybot(pid, "hello")
    assert sassybot_delay.call_args.args == (str(pid), str(svc._community_id), False)


def test_enqueue_forced_on_mention(sassybot_delay) -> None:
    svc = _svc()
    svc._enqueue_sassybot(__import__("uuid").uuid4(), "yo @sassybot")
    assert sassybot_delay.call_args.args[2] is True


def test_enqueue_failure_is_swallowed() -> None:
    with patch("app.tasks.ai_tasks.sassybot_comment_task.delay", side_effect=OSError):
        _svc()._enqueue_sassybot(__import__("uuid").uuid4(), "x")
