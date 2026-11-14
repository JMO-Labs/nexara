"""
@file test_poll_tasks.py
@brief Unit tests for poll maintenance Celery tasks.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import poll_tasks


def _factory(session):
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


async def test_close_expired_async_commits_and_returns_count():
    session = AsyncMock()
    repo_cls = MagicMock()
    repo_cls.return_value.close_expired = AsyncMock(return_value=4)
    with (
        patch.object(poll_tasks, "async_session_factory", _factory(session)),
        patch.object(poll_tasks, "PollRepository", repo_cls),
    ):
        result = await poll_tasks._close_expired_polls_async()
    assert result == {"closed_count": 4}
    session.commit.assert_awaited_once()


def test_close_expired_polls_entry_runs_async():
    with patch.object(
        poll_tasks, "_close_expired_polls_async", AsyncMock(return_value={"closed_count": 2})
    ):
        assert poll_tasks.close_expired_polls() == {"closed_count": 2}
