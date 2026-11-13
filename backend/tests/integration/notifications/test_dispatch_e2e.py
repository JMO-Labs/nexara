"""
@file test_dispatch_e2e.py
@brief Real Postgres + Valkey: notify() persists and publishes an SSE event.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
import app.services.notifications.types  # noqa: F401
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.notification_service import NotificationService
from app.services.notifications.dispatcher import Dispatcher
from app.services.realtime.event_bus import EventBus

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def test_notify_persists_and_emits_user_notification(session: AsyncSession):
    """@brief notify() stores the row and the bus receives a notification event."""
    user = User(
        community_id=COMMUNITY_ID,
        email=f"n_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"n_{uuid.uuid4().hex[:8]}",
        display_name="N",
    )
    session.add(user)
    await session.flush()

    bus = EventBus()
    bus.emit = AsyncMock(wraps=bus.emit)  # type: ignore[method-assign]
    svc = NotificationService(
        NotificationRepository(session),
        SettingsRepository(session),
        COMMUNITY_ID,
        dispatcher=Dispatcher(bus),
    )
    notif = await svc.notify(user.id, "mention", {"message": "hi", "actor_name": "Bob"})

    assert notif.id is not None
    bus.emit.assert_awaited_once()
    event = bus.emit.call_args.args[0]
    assert event.type.value == "notification"
    assert event.payload["id"] == str(notif.id)
    assert event.payload["type"] == "mention"
