"""
@file test_suggestions.py
@brief Unit tests for SuggestionService (prompt and poll generation).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.repositories.suggestion_repo import SuggestionRepository
from app.services.ai.provider import AIError, AIProvider
from app.services.ai.suggestion_service import SuggestionService

CID = uuid.uuid4()


def _repo(posts=("hello",), interests=("hiking",), events=("picnic",)):
    repo = AsyncMock(spec=SuggestionRepository)
    repo.recent_post_snippets.return_value = list(posts)
    repo.top_interests.return_value = list(interests)
    repo.upcoming_event_titles.return_value = list(events)
    repo.create.side_effect = lambda cid, t, c: MagicMock(type=t, content=c)
    return repo


def _provider(text: str):
    p = AsyncMock(spec=AIProvider)
    p.complete.return_value = (text, 0.1, 10)
    return p


class TestPrompts:
    async def test_returns_parsed_lines_max_100(self):
        text = "\n".join([f"Prompt {i}" for i in range(5)] + ["x" * 150])
        repo, prov = _repo(), _provider(text)
        out = await SuggestionService(repo, prov).generate_prompt_suggestions(CID)
        assert len(out) == 5
        assert all(len(s) <= 100 for s in out)
        assert repo.create.await_count == 5
        assert repo.create.await_args.args[1] == "prompt"

    async def test_prompt_contains_context(self):
        repo, prov = _repo(), _provider("a\nb")
        await SuggestionService(repo, prov).generate_prompt_suggestions(CID)
        sent = prov.complete.await_args.args[0]
        assert "hello" in sent and "hiking" in sent and "picnic" in sent
        repo.recent_post_snippets.assert_awaited_once_with(CID, 10)
        repo.top_interests.assert_awaited_once_with(CID, 5)
        repo.upcoming_event_titles.assert_awaited_once_with(CID, 5)

    async def test_no_context_skips(self):
        repo, prov = _repo(posts=(), interests=(), events=()), _provider("a")
        assert await SuggestionService(repo, prov).generate_prompt_suggestions(CID) == []
        prov.complete.assert_not_awaited()

    async def test_ai_failure_returns_empty(self):
        prov = _provider("")
        prov.complete.side_effect = AIError("boom")
        repo = _repo()
        assert await SuggestionService(repo, prov).generate_prompt_suggestions(CID) == []
        repo.create.assert_not_awaited()

    async def test_no_provider_returns_empty(self):
        assert await SuggestionService(_repo(), None).generate_prompt_suggestions(CID) == []


class TestPolls:
    async def test_question_and_four_options(self):
        repo, prov = _repo(), _provider("Best day?\nMon\nTue\nWed\nThu\nextra")
        res = await SuggestionService(repo, prov).generate_poll_suggestions(CID, "picnic")
        assert res == ("Best day?", ["Mon", "Tue", "Wed", "Thu"])
        assert "picnic" in prov.complete.await_args.args[0]
        assert repo.create.await_args.args[1] == "poll"
        assert repo.create.await_args.args[2] == {
            "question": "Best day?",
            "options": ["Mon", "Tue", "Wed", "Thu"],
            "topic": "picnic",
        }

    async def test_malformed_returns_none(self):
        repo, prov = _repo(), _provider("Only a question\nA")
        res = await SuggestionService(repo, prov).generate_poll_suggestions(CID, "t")
        assert res is None
        repo.create.assert_not_awaited()

    async def test_ai_failure_returns_none(self):
        prov = _provider("")
        prov.complete.side_effect = AIError("x")
        assert await SuggestionService(_repo(), prov).generate_poll_suggestions(CID, "t") is None


def test_lines_strips_numbering():
    from app.services.ai.suggestion_service import _lines

    assert _lines("1. one\n2) two\n- three\n\n") == ["one", "two", "three"]


class TestReviewPassthrough:
    async def test_list_approve_reject_delegate(self):
        repo = AsyncMock(spec=SuggestionRepository)
        svc = SuggestionService(repo, None)
        uid = uuid.uuid4()
        sid = uuid.uuid4()
        await svc.list_pending(CID, "poll", 5, 1)
        repo.list_pending.assert_awaited_once_with(CID, "poll", 5, 1)
        await svc.approve(sid, uid, CID)
        repo.approve.assert_awaited_once_with(sid, uid, CID)
        await svc.reject(sid, CID)
        repo.reject.assert_awaited_once_with(sid, CID)
