"""
@file test_age_admin_views.py
@brief Real Postgres: admin user list age fields, /users/me age source, and
       suggestion display names.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.admin import _user_to_admin_item
from app.api.v1.users import _detail
from app.models.age_suggestion import AgeSuggestion
from app.repositories.age_repo import AgeRepository
from tests.integration.repositories.nsfw_fixtures import (
    CID,
    adult,
    make_user,
    nsfw_session,  # noqa: F401 - provides the "session" fixture
    teen,
)

_APPROVAL = SimpleNamespace(adult_requires_approval=True)
_OPEN = SimpleNamespace(adult_requires_approval=False)


async def test_admin_list_item_has_set_and_effective_group(session) -> None:
    set_teen = await make_user(session, age_group="teen")
    grown = await adult(session)
    a = _user_to_admin_item(set_teen, _OPEN)
    assert (a.age_group, a.effective_age_group) == ("teen", "teen")
    b = _user_to_admin_item(grown, _APPROVAL)
    assert (b.age_group, b.effective_age_group) == (None, "unknown")
    assert _user_to_admin_item(grown, _OPEN).effective_age_group == "adult"


async def test_me_age_group_source(session) -> None:
    assert _detail(await make_user(session, age_group="adult"), _OPEN).age_group_source == "admin"
    assert _detail(await teen(session), _OPEN).age_group_source == "birthday"
    pending = _detail(await adult(session), _APPROVAL)
    assert (pending.age_group, pending.age_group_source) == ("unknown", "approval_pending")
    assert _detail(await make_user(session), _OPEN).age_group_source == "unknown"


async def test_suggestion_list_has_display_names(session) -> None:
    subject, by = await teen(session), await adult(session)
    session.add(
        AgeSuggestion(community_id=CID, subject_id=subject.id, suggested_by=by.id, age_group="teen")
    )
    await session.flush()
    rows = await AgeRepository(session).list(CID, "pending")
    names = {(r.subject_id, s, b) for r, s, b in rows}
    assert (subject.id, subject.display_name, by.display_name) in names
