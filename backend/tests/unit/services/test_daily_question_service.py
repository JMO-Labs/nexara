"""
@file test_daily_question_service.py
@brief Unit tests for DailyQuestionService (suggest, fire prep, reveal gating).
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, RateLimitError
from app.models.community import Community
from app.models.prompt import Prompt, PromptPost
from app.models.question_bank import QuestionBank
from app.repositories.question_bank_repo import QuestionBankRepository
from app.services.daily_question_service import SUGGESTIONS_PER_DAY, DailyQuestionService
from app.services.prompt_schedule import should_fire

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _community(on: bool = True) -> MagicMock:
    c = MagicMock(spec=Community)
    c.features = {"daily_question": on}
    return c


def _svc(on: bool = True) -> tuple[DailyQuestionService, AsyncMock]:
    repo = AsyncMock(spec=QuestionBankRepository)
    repo.count_builtin.return_value = 1
    session = AsyncMock()
    session.get.return_value = _community(on)
    return DailyQuestionService(repo, CID, session), repo


def _prompt(**kw: object) -> MagicMock:
    p = MagicMock(spec=Prompt)
    p.id = uuid.uuid4()
    p.frequency_type = "daily"
    p.is_enabled = True
    p.scope = "community"
    p.prompt_type = "daily_question"
    p.reveal_after_answer = True
    p.created_by = uuid.uuid4()
    for k, v in kw.items():
        setattr(p, k, v)
    return p


class TestShouldFireDaily:
    def test_any_date_true(self) -> None:
        assert should_fire(_prompt(), date(2026, 1, 1))
        assert should_fire(_prompt(), date(2026, 7, 19))

    def test_disabled_false(self) -> None:
        assert not should_fire(_prompt(is_enabled=False), date(2026, 1, 1))


class TestPrepareFire:
    async def test_sets_body_and_marks_used(self) -> None:
        svc, repo = _svc()
        row = MagicMock(spec=QuestionBank)
        row.text = "Best meal ever?"
        repo.next_question.return_value = row
        p = _prompt()
        assert await svc.prepare_fire(p) is True
        assert p.body == "Best meal ever?"
        repo.next_question.assert_awaited_once_with(CID, None)
        repo.mark_used.assert_awaited_once_with(row, None)

    async def test_group_prompt_tracks_own_use(self) -> None:
        svc, repo = _svc()
        repo.next_question.return_value = MagicMock(spec=QuestionBank, text="q")
        p = _prompt(scope="subgroup")
        await svc.prepare_fire(p)
        repo.next_question.assert_awaited_once_with(CID, p.id)

    async def test_feature_off_skips(self) -> None:
        svc, repo = _svc(on=False)
        assert await svc.prepare_fire(_prompt()) is False
        repo.next_question.assert_not_awaited()

    async def test_empty_bank_skips(self) -> None:
        svc, repo = _svc()
        repo.next_question.return_value = None
        assert await svc.prepare_fire(_prompt()) is False

    async def test_seeds_builtin_when_empty(self) -> None:
        svc, repo = _svc()
        repo.count_builtin.return_value = 0
        repo.next_question.return_value = MagicMock(spec=QuestionBank, text="q")
        await svc.prepare_fire(_prompt())
        repo.seed_builtin.assert_awaited_once()
        assert len(repo.seed_builtin.await_args.args[1]) == 200


class TestGating:
    async def test_locked_for_non_responder(self) -> None:
        svc, repo = _svc()
        repo.has_responded.return_value = False
        repo.count_responses.return_value = 2
        out = await svc.gate_responses(_prompt(), MagicMock(spec=PromptPost), uuid.uuid4())
        assert out == {"locked": True, "count": 2, "items": []}

    async def test_open_after_answering(self) -> None:
        svc, repo = _svc()
        repo.has_responded.return_value = True
        assert await svc.gate_responses(_prompt(), MagicMock(spec=PromptPost), uuid.uuid4()) is None

    async def test_creator_sees_items(self) -> None:
        svc, repo = _svc()
        p = _prompt()
        assert await svc.gate_responses(p, MagicMock(spec=PromptPost), p.created_by) is None
        repo.has_responded.assert_not_awaited()

    async def test_not_gated_without_flag(self) -> None:
        svc, _ = _svc()
        p = _prompt(reveal_after_answer=False)
        assert await svc.gate_responses(p, MagicMock(spec=PromptPost), uuid.uuid4()) is None


class TestSuggest:
    async def test_creates_pending(self) -> None:
        svc, repo = _svc()
        repo.count_suggestions_since.return_value = 0
        repo.create.side_effect = lambda r: r
        row = await svc.suggest(uuid.uuid4(), " Hi? ")
        assert (row.status, row.source, row.text) == ("pending", "member", "Hi?")

    async def test_fourth_in_a_day_is_rate_limited(self) -> None:
        svc, repo = _svc()
        repo.count_suggestions_since.return_value = SUGGESTIONS_PER_DAY
        with pytest.raises(RateLimitError) as exc:
            await svc.suggest(uuid.uuid4(), "x")
        assert exc.value.code == "RATE_LIMITED" and exc.value.status_code == 429

    async def test_feature_off_404(self) -> None:
        svc, _ = _svc(on=False)
        with pytest.raises(AppError) as exc:
            await svc.suggest(uuid.uuid4(), "x")
        assert exc.value.status_code == 404


def _group_data(**kw: object) -> MagicMock:
    base: dict[str, object] = {
        "prompt_type": "daily_question",
        "scope": "subgroup",
        "subgroup_id": uuid.uuid4(),
        "frequency_type": "daily",
        "notify_members": False,
        "linked_event_id": None,
        "active_days": 1,
    }
    base.update(kw)
    return MagicMock(**base)


class TestCanCreate:
    async def test_group_admin_may_create_group_daily(self) -> None:
        svc, repo = _svc()
        repo.is_group_admin.return_value = True
        data = _group_data()
        assert await svc.can_create(MagicMock(role="member", id=uuid.uuid4()), data)

    @pytest.mark.parametrize(
        "override",
        [
            {"notify_members": True},
            {"linked_event_id": uuid.uuid4()},
            {"frequency_type": "weekly"},
            {"active_days": 30},
        ],
    )
    async def test_group_admin_locked_down(self, override: dict[str, object]) -> None:
        svc, repo = _svc()
        repo.is_group_admin.return_value = True
        data = _group_data(**override)
        assert not await svc.can_create(MagicMock(role="member", id=uuid.uuid4()), data)

    async def test_member_cannot_create_standard(self) -> None:
        svc, repo = _svc()
        repo.is_group_admin.return_value = True
        data = MagicMock(prompt_type="standard", scope="subgroup", subgroup_id=uuid.uuid4())
        assert not await svc.can_create(MagicMock(role="member", id=uuid.uuid4()), data)
