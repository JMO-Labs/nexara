"""
@file test_profile_visibility.py
@brief Per-field profile privacy: defaults, levels, birthday, ProfileService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.profile_repo import ProfileRepository
from app.services.profiles.service import ProfileService
from app.services.profiles.visibility import allowed, birthday_view, effective_levels

CID = uuid.uuid4()


def test_defaults_legacy_follow_old_setting_new_are_private():
    lv = effective_levels(None, "community")
    assert lv["bio"] == "community" and lv["phone"] == "private"
    assert effective_levels({}, "admin_only")["bio"] == "private"
    assert effective_levels({"phone": "groups", "bio": "junk"}, "community")["phone"] == "groups"
    assert effective_levels({"bio": "junk"}, "community")["bio"] == "community"


def test_allowed_matrix():
    assert allowed("private", is_self=True, shares_group=False)
    assert not allowed("private", is_self=False, shares_group=True)
    assert allowed("groups", is_self=False, shares_group=True)
    assert not allowed("groups", is_self=False, shares_group=False)
    assert allowed("community", is_self=False, shares_group=False)


def test_birthday_view():
    b = date(1990, 3, 7)
    kw = {"is_self": False, "viewer_is_admin": False}
    assert birthday_view(b, show_to="community", show_year=False, **kw) == "--03-07"
    assert birthday_view(b, show_to="community", show_year=True, **kw) == "1990-03-07"
    assert birthday_view(b, show_to="nobody", show_year=True, **kw) is None
    assert birthday_view(b, show_to="nobody", show_year=False, is_self=True, viewer_is_admin=False)
    assert birthday_view(
        b, show_to="admin_only", show_year=False, is_self=False, viewer_is_admin=True
    )


def _target() -> MagicMock:
    u = MagicMock(spec=User)
    u.id, u.username, u.display_name, u.role = uuid.uuid4(), "ruth", "Ruth", "member"
    u.avatar_url = u.banner_media_id = None
    u.created_at = datetime.now(UTC)
    u.last_seen_at = None
    u.birthday = date(1948, 11, 24)
    u.bio, u.title, u.pronouns, u.location, u.website_url = "Hi", None, "she/her", "Phoenix", None
    u.phone, u.contact_email, u.address = "555-0100", "ruth@x.io", "1 Main St"
    u.links, u.skills = [{"label": "", "url": "https://instagram.com/ruth"}], ["quilting"]
    u.emergency_contact = {"name": "Sam", "phone": "555-0199", "relation": "son"}
    u.availability = u.dietary = None
    return u


def _settings(vis: dict[str, str]) -> MagicMock:
    s = MagicMock(spec=UserSettings)
    s.field_visibility, s.profile_visible_to = vis, "community"
    s.show_birthday_to, s.show_birthday_year, s.show_last_seen = "community", False, True
    return s


def _svc(target, settings, shares=False):
    repo = AsyncMock(spec=ProfileRepository)
    repo.get_user.return_value = target
    repo.get_settings.return_value = settings
    repo.shares_group.return_value = shares
    return ProfileService(repo, CID), repo


def _viewer(uid=None) -> MagicMock:
    v = MagicMock(spec=User)
    v.id, v.role = uid or uuid.uuid4(), "member"
    return v


async def test_stranger_sees_only_community_fields():
    t = _target()
    svc, repo = _svc(t, _settings({"phone": "groups", "links": "community"}), shares=False)
    p = await svc.view(t.id, _viewer())
    assert p.bio == "Hi" and p.location == "Phoenix"
    assert p.phone is None and p.address is None and p.emergency_contact is None
    assert p.links[0].url.endswith("/ruth")
    assert p.birthday == "--11-24" and p.field_visibility is None


async def test_group_mate_sees_groups_fields():
    t = _target()
    svc, _ = _svc(t, _settings({"phone": "groups"}), shares=True)
    p = await svc.view(t.id, _viewer())
    assert p.phone == "555-0100" and p.contact_email is None


async def test_self_sees_everything_and_levels():
    t = _target()
    svc, repo = _svc(t, _settings({}))
    p = await svc.view(t.id, _viewer(t.id))
    assert p.phone == "555-0100" and p.emergency_contact is not None
    assert p.birthday == "1948-11-24"
    assert p.field_visibility and p.field_visibility["phone"] == "private"
    repo.shares_group.assert_not_awaited()


async def test_unknown_user_404():
    svc, repo = _svc(None, None)
    with pytest.raises(NotFoundError):
        await svc.view(uuid.uuid4(), _viewer())
