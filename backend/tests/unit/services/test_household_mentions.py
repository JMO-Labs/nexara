"""@file test_household_mentions.py @brief @handle mentions of pets/household members."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.household_handles import slugify, unique_handle
from app.services.household_mentions import sync_household_tags

CID = uuid.uuid4()
ACTOR = SimpleNamespace(id=uuid.uuid4(), display_name="Maya")


def test_slugify():
    assert slugify("Mr. Biscuit!", "pet") == "mr-biscuit"
    assert slugify("  ", "pet") == "pet"
    assert slugify("Ünïcode", "person") == "n-code"
    assert len(slugify("x" * 80, "pet")) <= 30


async def test_unique_handle_skips_taken():
    taken = {"biscuit", "biscuit-2"}

    async def is_taken(h: str) -> bool:
        return h in taken

    assert await unique_handle("Biscuit", "pet", is_taken) == "biscuit-3"


def _post(**kw):
    return SimpleNamespace(
        **{"id": uuid.uuid4(), "visibility": "community", "subgroup_id": None, **kw}
    )


async def test_tags_visible_members_and_notifies_owner_once():
    pet, owner = uuid.uuid4(), uuid.uuid4()
    own_pet = uuid.uuid4()
    tags, notif = AsyncMock(), AsyncMock()
    tags.household_by_handles.return_value = [(pet, owner), (own_pet, ACTOR.id)]
    tags.replace_user_tags.return_value = [pet, own_pet]
    tags.blocked_with.return_value = []
    post = _post()
    await sync_household_tags(tags, notif, CID, "post", post.id, ["biscuit", "rex"], ACTOR, post)
    tags.household_by_handles.assert_awaited_with(CID, ACTOR.id, ["biscuit", "rex"])
    assert tags.replace_user_tags.await_args.kwargs["subject_type"] == "household"
    assert notif.notify.await_count == 1  # not for the actor's own pet
    assert notif.notify.await_args.kwargs["user_id"] == owner


async def test_private_post_clears_and_blocked_owner_not_notified():
    tags, notif = AsyncMock(), AsyncMock()
    tags.replace_user_tags.return_value = []
    post = _post(visibility="private")
    await sync_household_tags(tags, notif, CID, "post", post.id, ["biscuit"], ACTOR, post)
    tags.household_by_handles.assert_not_awaited()
    assert tags.replace_user_tags.await_args.args[3] == []
    pet, owner = uuid.uuid4(), uuid.uuid4()
    tags.household_by_handles.return_value = [(pet, owner)]
    tags.replace_user_tags.return_value = [pet]
    tags.blocked_with.return_value = [owner]
    post = _post()
    await sync_household_tags(tags, notif, CID, "post", post.id, ["biscuit"], ACTOR, post)
    notif.notify.assert_not_awaited()
