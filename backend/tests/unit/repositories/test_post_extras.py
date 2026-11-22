"""@file test_post_extras.py @brief Feed extras: kudos recipient and celebrations."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.repositories.post_extras import post_extras

CID = uuid.uuid4()


def _post(**kw):
    base = {
        "id": uuid.uuid4(),
        "community_id": CID,
        "recipient_id": None,
        "celebrate_type": None,
        "celebrate_id": None,
        "celebrate_occasion": None,
    }
    return SimpleNamespace(**{**base, **kw})


def _result(rows):
    r = MagicMock()
    r.scalars.return_value = rows
    return r


async def test_plain_posts_skip_queries():
    session = AsyncMock()
    out = await post_extras(session, [_post()], uuid.uuid4())
    session.execute.assert_not_awaited()
    assert list(out.values())[0] == {"recipient_id": None, "recipient": None, "celebration": None}


async def test_kudos_recipient_and_user_celebration():
    ruth = SimpleNamespace(id=uuid.uuid4(), username="ruth", display_name="Ruth", avatar_url=None)
    kudos = _post(recipient_id=ruth.id)
    bday = _post(celebrate_type="user", celebrate_id=ruth.id, celebrate_occasion="birthday")
    session = AsyncMock()
    session.execute.return_value = _result([ruth])
    out = await post_extras(session, [kudos, bday], uuid.uuid4())
    assert out[kudos.id]["recipient"]["username"] == "ruth"
    assert out[bday.id]["celebration"]["link"] == "/app/u/ruth"


async def test_hidden_pet_reveals_nothing():
    pet_post = _post(
        celebrate_type="household", celebrate_id=uuid.uuid4(), celebrate_occasion="gotcha_day"
    )
    session = AsyncMock()
    session.execute.return_value = _result([])  # viewer can't see the pet
    out = await post_extras(session, [pet_post], uuid.uuid4())
    c = out[pet_post.id]["celebration"]
    assert c["name"] is None and c["link"] is None and c["subject_id"] is None
