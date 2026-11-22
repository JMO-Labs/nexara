"""@file test_post_celebrate.py @brief Celebrate posts: who may be celebrated, who hears."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ValidationError
from app.schemas.post import CelebrateIn
from app.services import post_celebrate

CID = uuid.uuid4()
ACTOR = SimpleNamespace(id=uuid.uuid4(), display_name="Maya")


async def test_resolve_rules():
    repo = AsyncMock()
    ruth = SimpleNamespace(id=uuid.uuid4(), display_name="Ruth")
    repo.celebratable_user.return_value = ruth
    got = await post_celebrate.resolve(
        repo, CID, ACTOR, CelebrateIn(subject_type="user", subject_id=ruth.id)
    )
    assert (got.notify_id, got.occasion) == (ruth.id, "birthday")
    with pytest.raises(ValidationError):  # people don't have gotcha days
        await post_celebrate.resolve(
            repo,
            CID,
            ACTOR,
            CelebrateIn(subject_type="user", subject_id=ruth.id, occasion="gotcha_day"),
        )
    repo.celebratable_user.return_value = None  # blocked / other community
    with pytest.raises(ValidationError):
        await post_celebrate.resolve(
            repo, CID, ACTOR, CelebrateIn(subject_type="user", subject_id=ruth.id)
        )
    owner = uuid.uuid4()
    repo.celebratable_household.return_value = SimpleNamespace(
        id=uuid.uuid4(), kind="pet", name="Biscuit", owner_id=owner
    )
    pet = await post_celebrate.resolve(
        repo,
        CID,
        ACTOR,
        CelebrateIn(subject_type="household", subject_id=uuid.uuid4(), occasion="gotcha_day"),
    )
    assert pet.notify_id == owner and pet.name == "Biscuit"
    repo.celebratable_household.return_value = None  # can't see the pet
    with pytest.raises(ValidationError):
        await post_celebrate.resolve(
            repo, CID, ACTOR, CelebrateIn(subject_type="household", subject_id=uuid.uuid4())
        )


async def test_notify_skips_self():
    notif = AsyncMock()
    me = post_celebrate.Celebrated("user", ACTOR.id, "birthday", "Maya", ACTOR.id)
    await post_celebrate.notify(notif, ACTOR, me, uuid.uuid4())
    notif.notify.assert_not_awaited()
    pet = post_celebrate.Celebrated("household", uuid.uuid4(), "birthday", "Biscuit", uuid.uuid4())
    await post_celebrate.notify(notif, ACTOR, pet, uuid.uuid4())
    assert "Biscuit" in notif.notify.await_args.kwargs["payload"]["message"]
