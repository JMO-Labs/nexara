"""@file factory.py
@brief Public builder for a session-bound NotificationService.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService


def build_notification_service(
    session: AsyncSession, community_id: uuid.UUID
) -> NotificationService:
    """@brief Build a NotificationService bound to ``session`` (lazy imports avoid cycles)."""
    from app.core.dependencies import get_dispatcher
    from app.repositories.notification_repo import NotificationRepository
    from app.repositories.settings_repo import SettingsRepository
    from app.services.notification_service import NotificationService

    return NotificationService(
        notification_repo=NotificationRepository(session),
        settings_repo=SettingsRepository(session),
        community_id=community_id,
        dispatcher=get_dispatcher(),
    )
