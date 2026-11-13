"""
@file test_notification_service_api.py
@brief Unit tests for NotificationService methods backing the API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.notifications.types  # noqa: F401  (registers built-ins)
from app.core.exceptions import AppError, NotFoundError
from app.models.user_settings import UserSettings
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.notification import NotificationPreferencesUpdate
from app.services.notification_service import NotificationService
from app.services.notifications.dispatcher import Dispatcher

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _settings_row() -> MagicMock:
    row = MagicMock(spec=UserSettings)
    row.notification_prefs = {"mention": {"email": False}}
    row.dnd_schedule = None
    row.dnd_until = None
    row.dnd_timezone = "UTC"
    row.digest_cadence = {}
    return row


def _build() -> tuple[NotificationService, AsyncMock, AsyncMock, MagicMock]:
    repo = AsyncMock(spec=NotificationRepository)
    settings_repo = AsyncMock(spec=SettingsRepository)
    row = _settings_row()
    settings_repo.get_or_create.return_value = row
    settings_repo.update.return_value = row
    repo.list_for_user.return_value = ([], None)
    svc = NotificationService(
        repo, settings_repo, COMMUNITY_ID, dispatcher=AsyncMock(spec=Dispatcher)
    )
    return svc, repo, settings_repo, row


class TestListFilters:
    async def test_type_filter(self) -> None:
        svc, repo, _, _ = _build()
        await svc.list_for_user(USER_ID, type="mention", unread_only=True)
        kw = repo.list_for_user.await_args.kwargs
        assert kw["types"] == ["mention"]
        assert kw["unread_only"] is True

    async def test_category_filter_expands_to_type_keys(self) -> None:
        svc, repo, _, _ = _build()
        await svc.list_for_user(USER_ID, category="event")
        types = repo.list_for_user.await_args.kwargs["types"]
        assert set(types) == {"event_reminder", "event_rsvp"}

    async def test_no_filter_passes_none(self) -> None:
        svc, repo, _, _ = _build()
        await svc.list_for_user(USER_ID)
        assert repo.list_for_user.await_args.kwargs["types"] is None

    async def test_unknown_type_raises_400(self) -> None:
        svc, repo, _, _ = _build()
        with pytest.raises(AppError) as exc:
            await svc.list_for_user(USER_ID, type="nope")
        assert exc.value.code == "NOTIF_TYPE_UNKNOWN"
        assert exc.value.status_code == 400
        repo.list_for_user.assert_not_awaited()


class TestUnreadCount:
    async def test_groups_by_category(self) -> None:
        svc, repo, _, _ = _build()
        repo.unread_counts_by_type.return_value = {
            "mention": 2,
            "comment": 1,
            "event_rsvp": 4,
            "legacy_gone": 1,
        }
        res = await svc.get_unread_count(USER_ID)
        assert res.count == 8
        assert res.by_category == {"social": 3, "event": 4, "system": 1}


class TestBulkAndDelete:
    async def test_mark_all_read_by_category(self) -> None:
        svc, repo, _, _ = _build()
        repo.mark_all_read.return_value = 2
        assert await svc.mark_all_read(USER_ID, category="gallery") == 2
        types = repo.mark_all_read.await_args.kwargs["types"]
        assert set(types) == {"gallery_activity", "gallery_reminder"}

    async def test_clear_all_with_type_and_before(self) -> None:
        svc, repo, _, _ = _build()
        before = datetime(2026, 1, 1, tzinfo=UTC)
        repo.delete_all_for_user.return_value = 1
        assert await svc.clear_all(USER_ID, type="mention", before=before) == 1
        repo.delete_all_for_user.assert_awaited_once_with(USER_ID, types=["mention"], before=before)

    async def test_delete_missing_raises_not_found(self) -> None:
        svc, repo, _, _ = _build()
        repo.delete_one.return_value = False
        with pytest.raises(NotFoundError):
            await svc.delete(USER_ID, uuid.uuid4())

    async def test_delete_ok(self) -> None:
        svc, repo, _, _ = _build()
        nid = uuid.uuid4()
        repo.delete_one.return_value = True
        await svc.delete(USER_ID, nid)
        repo.delete_one.assert_awaited_once_with(USER_ID, nid)


class TestPreferences:
    async def test_get(self) -> None:
        svc, _, _, _ = _build()
        prefs = await svc.get_preferences(USER_ID)
        assert prefs.notification_prefs == {"mention": {"email": False}}
        assert prefs.dnd_timezone == "UTC"

    async def test_patch_merges_type_prefs(self) -> None:
        svc, _, settings_repo, _ = _build()
        patch = NotificationPreferencesUpdate(notification_prefs={"mention": {"push": False}})
        await svc.update_preferences(USER_ID, patch)
        data = settings_repo.update.await_args.args[1]
        assert data == {"notification_prefs": {"mention": {"email": False, "push": False}}}

    async def test_patch_only_sets_given_fields(self) -> None:
        svc, _, settings_repo, _ = _build()
        patch = NotificationPreferencesUpdate(
            dnd_timezone="America/New_York", dnd_schedule=None, digest_cadence={"mention": "daily"}
        )
        await svc.update_preferences(USER_ID, patch)
        data = settings_repo.update.await_args.args[1]
        assert data == {
            "dnd_timezone": "America/New_York",
            "dnd_schedule": None,
            "digest_cadence": {"mention": "daily"},
        }

    @pytest.mark.parametrize(
        ("body", "code"),
        [
            ({"notification_prefs": {"nope": {"email": True}}}, "NOTIF_TYPE_UNKNOWN"),
            ({"notification_prefs": {"mention": {"webhook": True}}}, "NOTIF_PREF_INVALID"),
            ({"dnd_timezone": "Mars/Base"}, "NOTIF_PREF_INVALID"),
            ({"digest_cadence": {"mention": "yearly"}}, "NOTIF_PREF_INVALID"),
            ({"digest_cadence": {"nope": "daily"}}, "NOTIF_TYPE_UNKNOWN"),
        ],
    )
    async def test_patch_invalid(self, body: dict[str, object], code: str) -> None:
        svc, _, settings_repo, _ = _build()
        with pytest.raises(AppError) as exc:
            await svc.update_preferences(USER_ID, NotificationPreferencesUpdate(**body))  # type: ignore[arg-type]
        assert exc.value.code == code
        assert exc.value.status_code == 400
        settings_repo.update.assert_not_awaited()
