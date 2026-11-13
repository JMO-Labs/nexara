"""
@file test_notification_dismiss_event.py
@brief NotificationService.dismiss emits user_notification_dismissed.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.notifications.dispatcher import Dispatcher
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import EventType, UserTarget

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _svc(bus: AsyncMock | None) -> tuple[NotificationService, AsyncMock]:
    repo = AsyncMock(spec=NotificationRepository)
    svc = NotificationService(
        repo,
        AsyncMock(spec=SettingsRepository),
        COMMUNITY_ID,
        event_bus=bus,
        dispatcher=AsyncMock(spec=Dispatcher),
    )
    return svc, repo


async def test_dismiss_emits_event_to_user_only() -> None:
    bus = AsyncMock(spec=EventBus)
    svc, _ = _svc(bus)
    nid = uuid.uuid4()
    await svc.dismiss(USER_ID, nid)
    bus.emit.assert_awaited_once()
    ev = bus.emit.await_args.args[0]
    assert ev.type == EventType.USER_NOTIFICATION_DISMISSED
    assert ev.type == "user_notification_dismissed"
    assert isinstance(ev.target, UserTarget)
    assert ev.target.user_id == USER_ID
    assert ev.payload == {"user_id": str(USER_ID), "notification_ids": [str(nid)]}


async def test_dismiss_without_bus_does_not_emit() -> None:
    svc, repo = _svc(None)
    await svc.dismiss(USER_ID, uuid.uuid4())
    repo.dismiss.assert_awaited_once()


async def test_dismiss_failure_does_not_emit() -> None:
    bus = AsyncMock(spec=EventBus)
    svc, repo = _svc(bus)
    repo.dismiss.side_effect = NotFoundError("Notification not found")
    with pytest.raises(NotFoundError):
        await svc.dismiss(USER_ID, uuid.uuid4())
    bus.emit.assert_not_awaited()
