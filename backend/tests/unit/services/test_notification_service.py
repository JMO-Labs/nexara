"""
@file test_notification_service.py
@brief Unit tests for the NotificationService façade.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.notifications.types  # noqa: F401  (registers built-ins)
from app.core.exceptions import AppError
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.notifications.dispatcher import Dispatcher

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
PAYLOAD = {"message": "Hi", "actor_name": "Bob"}


def _build(prefs: dict | None = None):
    repo = AsyncMock(spec=NotificationRepository)
    settings_repo = AsyncMock(spec=SettingsRepository)
    row = MagicMock()
    row.notification_prefs = prefs or {}
    row.dnd_schedule = None
    row.dnd_until = None
    row.dnd_timezone = "UTC"
    settings_repo.get_or_create.return_value = row
    dispatcher = AsyncMock(spec=Dispatcher)
    notif = MagicMock(spec=Notification)
    repo.upsert_grouped.return_value = notif
    svc = NotificationService(repo, settings_repo, COMMUNITY_ID, dispatcher=dispatcher)
    return svc, repo, dispatcher, notif


class TestNotify:
    """@brief notify() orchestration."""

    async def test_happy_path_persists_and_dispatches(self):
        svc, repo, dispatcher, notif = _build()
        result = await svc.notify(USER_ID, "mention", PAYLOAD)
        assert result is notif
        repo.upsert_grouped.assert_awaited_once()
        assert repo.upsert_grouped.call_args.kwargs["group_key"] is None
        dispatcher.dispatch.assert_awaited_once()

    async def test_dispatch_gets_effective_channels(self):
        svc, _, dispatcher, notif = _build({"mention": {"email": False}})
        await svc.notify(USER_ID, "mention", PAYLOAD)
        args = dispatcher.dispatch.call_args.args
        assert args[0] is notif
        assert args[1].key == "mention"
        assert args[2]["email"] is False
        assert args[2]["inapp"] is True

    async def test_unknown_type_raises_400(self):
        svc, repo, dispatcher, _ = _build()
        with pytest.raises(AppError) as exc:
            await svc.notify(USER_ID, "nope", PAYLOAD)
        assert exc.value.code == "NOTIF_TYPE_UNKNOWN"
        assert exc.value.status_code == 400
        repo.upsert_grouped.assert_not_awaited()
        dispatcher.dispatch.assert_not_awaited()

    async def test_invalid_payload_raises_400(self):
        svc, repo, dispatcher, _ = _build()
        with pytest.raises(AppError) as exc:
            await svc.notify(USER_ID, "mention", {"message": "x"})
        assert exc.value.code == "NOTIF_PREF_INVALID"
        assert exc.value.status_code == 400
        repo.upsert_grouped.assert_not_awaited()
        dispatcher.dispatch.assert_not_awaited()


class TestGrouping:
    async def test_passes_group_key_and_window(self):
        svc, repo, _, _ = _build()
        await svc.notify(USER_ID, "comment", {**PAYLOAD, "target_id": "p1"}, actor_id=USER_ID)
        kw = repo.upsert_grouped.call_args.kwargs
        assert kw["group_key"] == "comment:p1"
        assert kw["group_window_seconds"] == 300
        assert kw["actor_id"] == USER_ID
        assert kw["community_id"] == COMMUNITY_ID


class TestWrappers:
    """@brief Thin repo-delegating wrappers."""

    async def test_list_active_dismiss_dismiss_all(self):
        svc, repo, _, _ = _build()
        repo.list_active.return_value = []
        repo.dismiss_all.return_value = 3
        assert await svc.list_active(USER_ID, limit=5) == []
        repo.list_active.assert_awaited_once_with(USER_ID, 5)
        nid = uuid.uuid4()
        await svc.dismiss(USER_ID, nid)
        repo.dismiss.assert_awaited_once_with(USER_ID, nid)
        assert await svc.dismiss_all(USER_ID) == 3

    def test_notify_mentions_removed(self):
        import importlib

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("app.services.mention_notify")

    async def test_default_dispatcher_used_without_event_bus(self):
        repo = AsyncMock(spec=NotificationRepository)
        settings_repo = AsyncMock(spec=SettingsRepository)
        row = MagicMock()
        row.notification_prefs = {}
        row.dnd_schedule = None
        row.dnd_until = None
        row.dnd_timezone = "UTC"
        settings_repo.get_or_create.return_value = row
        repo.upsert_grouped.return_value = MagicMock(spec=Notification)
        disp = AsyncMock(spec=Dispatcher)
        with patch("app.core.dependencies.get_dispatcher", return_value=disp):
            svc = NotificationService(repo, settings_repo, COMMUNITY_ID)
        await svc.notify(USER_ID, "system", PAYLOAD)
        disp.dispatch.assert_awaited_once()


class TestDndGating:
    async def test_snoozed_suppresses_external_channels(self):
        from datetime import UTC, datetime, timedelta

        svc, repo, dispatcher, _ = _build()
        row = svc._settings_repo.get_or_create.return_value
        row.dnd_until = datetime.now(UTC) + timedelta(hours=1)
        await svc.notify(USER_ID, "mention", PAYLOAD)
        eff = dispatcher.dispatch.call_args.args[2]
        assert eff["inapp"] is True
        assert not (eff["email"] or eff["push"] or eff["toast"])

    async def test_bypass_type_not_suppressed(self):
        from datetime import UTC, datetime, timedelta

        svc, repo, dispatcher, _ = _build()
        row = svc._settings_repo.get_or_create.return_value
        row.dnd_until = datetime.now(UTC) + timedelta(hours=1)
        await svc.notify(USER_ID, "system", PAYLOAD)
        eff = dispatcher.dispatch.call_args.args[2]
        assert eff["email"] is True or eff["push"] is True or eff["toast"] is True


class TestSnoozeMethods:
    async def test_set_dnd_snooze_clear(self):
        from datetime import UTC, datetime

        svc, *_ = _build()
        repo = svc._settings_repo
        repo.update.return_value = MagicMock(
            notification_prefs={}, dnd_schedule=None, dnd_until=None,
            dnd_timezone="UTC", digest_cadence={},
        )
        await svc.set_dnd(USER_ID, {"mon": []}, "UTC")
        repo.update.assert_awaited_with(
            USER_ID, {"dnd_schedule": {"mon": []}, "dnd_timezone": "UTC"}
        )
        until = datetime(2026, 1, 1, tzinfo=UTC)
        await svc.snooze(USER_ID, until)
        repo.update.assert_awaited_with(USER_ID, {"dnd_until": until})
        await svc.clear_snooze(USER_ID)
        repo.update.assert_awaited_with(USER_ID, {"dnd_until": None})
