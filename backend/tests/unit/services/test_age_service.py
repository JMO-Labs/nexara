"""
@file test_age_service.py
@brief Unit tests for age group derivation and AgeService.
"""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.models.age_suggestion import AgeSuggestion
from app.repositories.age_repo import AgeRepository
from app.services.age_service import AgeService, effective_age_group, is_adult

CID = uuid.uuid4()


def _bday(years: int) -> date:
    t = date.today()
    return date(t.year - years - 1, t.month, 1 if t.day > 28 else t.day)


def _u(birthday=None, group=None):
    return SimpleNamespace(birthday=birthday, age_group=group)


def test_birthday_15_is_teen():
    assert effective_age_group(_u(_bday(15)), None) == "teen"


def test_birthday_10_is_child():
    assert effective_age_group(_u(_bday(10)), None) == "child"


def test_admin_set_adult_overrides_birthday():
    assert effective_age_group(_u(_bday(10), "adult"), None) == "adult"


def test_approval_mode_birthday_adult_is_unknown():
    c = SimpleNamespace(adult_requires_approval=True)
    assert effective_age_group(_u(_bday(30)), c) == "unknown"
    assert is_adult(_u(_bday(30)), c) is False
    assert is_adult(_u(_bday(30), "adult"), c) is True


def test_no_birthday_unknown():
    assert effective_age_group(_u(), None) == "unknown"


def _svc(actor):
    repo = AsyncMock(spec=AgeRepository)
    audit = MagicMock(append=AsyncMock())
    notifier = MagicMock(notify=AsyncMock())
    return AgeService(repo, CID, actor, audit, notifier), repo, audit, notifier


async def test_suggest_self_400():
    me = uuid.uuid4()
    svc, *_ = _svc(me)
    with pytest.raises(AppError) as e:
        await svc.suggest(me, "teen", None)
    assert e.value.status_code == 400


async def test_suggest_notifies_admins_never_subject():
    me, subj, admin = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    svc, repo, _a, notifier = _svc(me)
    repo.get_user.return_value = _u()
    repo.pending_exists.return_value = False
    repo.list_admin_ids.return_value = [admin, subj]
    repo.create.return_value = MagicMock(spec=AgeSuggestion)
    await svc.suggest(subj, "teen", "n")
    targets = [c.kwargs["user_id"] for c in notifier.notify.await_args_list]
    assert targets == [admin]


async def test_approve_sets_group_and_audits():
    admin, subj = uuid.uuid4(), uuid.uuid4()
    svc, repo, audit, _n = _svc(admin)
    row = MagicMock(spec=AgeSuggestion, id=uuid.uuid4(), subject_id=subj, age_group="teen")
    row.status = "pending"
    user = _u()
    repo.get.return_value = row
    repo.get_user.return_value = user
    await svc.decide(row.id, True)
    repo.set_user_group.assert_awaited_with(user, "teen")
    assert audit.append.await_args.kwargs["action"] == "age_group.suggestion.approved"


async def test_decide_twice_409():
    svc, repo, *_ = _svc(uuid.uuid4())
    row = MagicMock(spec=AgeSuggestion)
    row.status = "approved"
    repo.get.return_value = row
    with pytest.raises(AppError) as e:
        await svc.decide(uuid.uuid4(), False)
    assert e.value.status_code == 409
