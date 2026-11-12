"""
@file test_birthday_service.py
@brief Unit tests for BirthdayService privacy filtering and notification.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.repositories.birthday_repo import BirthdayRepository
from app.repositories.post_repo import PostRepository
from app.services.birthday_service import BirthdayService
from app.services.notification_service import PREF_MAP

TODAY = date(2026, 5, 4)


def _user(name="Ann"):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.display_name = name
    return u


def _svc(birthdays, members, admins, auto_post=False):
    repo = AsyncMock(spec=BirthdayRepository)
    repo.list_birthday_users.return_value = birthdays
    repo.list_member_ids.return_value = members
    repo.list_admin_ids.return_value = admins
    notif = AsyncMock()
    posts = AsyncMock(spec=PostRepository)
    svc = BirthdayService(repo, notif, posts, uuid.uuid4(), auto_post=auto_post)
    return svc, notif, posts


def test_pref_map_has_birthday_reminder():
    assert PREF_MAP["birthday_reminder"] == ("notif_birthday_inapp", "notif_birthday_email")


async def test_nobody_skips_everything():
    svc, notif, posts = _svc([(_user(), "nobody")], [uuid.uuid4()], [], auto_post=True)
    assert await svc.send_reminders(TODAY) == 0
    notif.notify.assert_not_called()
    posts.create_post.assert_not_called()


async def test_community_notifies_all_but_self():
    ann = _user()
    a, b = uuid.uuid4(), uuid.uuid4()
    svc, notif, _ = _svc([(ann, "community")], [a, b, ann.id], [])
    assert await svc.send_reminders(TODAY) == 2
    assert notif.notify.await_count == 2
    kwargs = notif.notify.await_args_list[0].kwargs
    assert kwargs["type"] == "birthday_reminder"
    assert kwargs["payload"]["message"] == "Ann's birthday is today!"
    assert kwargs["actor_id"] == ann.id


async def test_admin_only_notifies_admins():
    adm = uuid.uuid4()
    svc, notif, _ = _svc([(_user(), "admin_only")], [uuid.uuid4()], [adm])
    assert await svc.send_reminders(TODAY) == 1
    assert notif.notify.await_args.kwargs["user_id"] == adm


async def test_auto_post_created_for_community_visible():
    ann = _user()
    svc, _, posts = _svc([(ann, "community")], [], [], auto_post=True)
    await svc.send_reminders(TODAY)
    posts.create_post.assert_awaited_once()
    assert "Ann" in posts.create_post.await_args.kwargs["content"]


async def test_no_post_for_admin_only_or_when_disabled():
    svc, _, posts = _svc([(_user(), "admin_only")], [], [uuid.uuid4()], auto_post=True)
    await svc.send_reminders(TODAY)
    posts.create_post.assert_not_called()
    svc, _, posts = _svc([(_user(), "community")], [], [], auto_post=False)
    await svc.send_reminders(TODAY)
    posts.create_post.assert_not_called()
