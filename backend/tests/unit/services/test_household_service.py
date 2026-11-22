"""
@file test_household_service.py
@brief HouseholdService: birth-year/care-card privacy, owner-only edits,
       pet-only fields, upcoming celebrations.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.household import HouseholdMember
from app.models.user import User
from app.repositories.household_repo import HouseholdRepository
from app.schemas.household import HouseholdCreate, HouseholdUpdate
from app.services.household_service import HouseholdService

CID = uuid.uuid4()


def _user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    return u


def _member(owner: uuid.UUID, **kw: object) -> MagicMock:
    m = MagicMock(spec=HouseholdMember)
    base = dict(
        id=uuid.uuid4(),
        owner_id=owner,
        kind="pet",
        name="Biscuit",
        relation=None,
        birthday=date(2019, 11, 25),
        show_birth_year=False,
        photo_media_id=None,
        visibility="groups",
        bio=None,
        species="Dog",
        breed=None,
        gotcha_day=None,
        likes=["walks"],
        dislikes=[],
        care_card="2 cups kibble",
        care_visibility="private",
    )
    base.update(kw)
    for k, v in base.items():
        setattr(m, k, v)
    return m


def _svc() -> tuple[HouseholdService, AsyncMock]:
    repo = AsyncMock(spec=HouseholdRepository)
    repo.care_visible.return_value = False
    repo.media_in_community.return_value = True
    repo.visible.return_value = []
    return HouseholdService(repo, CID), repo


async def test_viewer_gets_hidden_year_and_no_care_card():
    svc, repo = _svc()
    owner, viewer = _user(), _user()
    m = _member(owner.id)
    v = await svc.view(m, viewer)
    assert v["birthday"] == "--11-25" and v["care_card"] is None and not v["can_edit"]
    mine = await svc.view(m, owner)
    assert mine["birthday"] == "2019-11-25" and mine["care_card"] == "2 cups kibble"
    repo.care_visible.return_value = True
    assert (await svc.view(m, viewer))["care_card"] == "2 cups kibble"


async def test_only_owner_edits():
    svc, repo = _svc()
    owner = _user()
    repo.get_visible.return_value = _member(owner.id)
    with pytest.raises(NotFoundError):
        await svc.update(uuid.uuid4(), _user(), HouseholdUpdate(name="X"))
    repo.update.return_value = _member(owner.id, name="Bis")
    await svc.update(uuid.uuid4(), owner, HouseholdUpdate(name=" Bis "))
    assert repo.update.await_args.args[1] == {"name": "Bis"}


async def test_person_drops_pet_fields_and_photo_must_exist():
    svc, repo = _svc()
    user = _user()
    repo.create.return_value = _member(user.id, kind="person")
    await svc.create(user, HouseholdCreate(kind="person", name="Mia", species="Cat"))
    assert "species" not in repo.create.await_args.kwargs
    repo.media_in_community.return_value = False
    with pytest.raises(ValidationError):
        await svc.create(user, HouseholdCreate(kind="pet", name="X", photo_media_id=uuid.uuid4()))


async def test_upcoming_lists_birthdays_and_gotcha_days_soonest_first():
    svc, repo = _svc()
    viewer = _user()
    repo.visible.return_value = [
        _member(viewer.id, birthday=date(2019, 11, 30), gotcha_day=date(2020, 11, 22)),
        _member(viewer.id, birthday=date(2001, 6, 1)),
    ]
    out = await svc.upcoming(viewer, date(2026, 11, 21))
    assert [(c["occasion"], c["in_days"]) for c in out] == [("gotcha_day", 1), ("birthday", 9)]


def test_lists_are_trimmed_and_deduped():
    u = HouseholdUpdate(likes=[" walks ", "walks", "", "naps"])
    assert u.likes == ["walks", "naps"]
