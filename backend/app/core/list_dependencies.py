"""
@file list_dependencies.py
@brief FastAPI dependency providers for the lists / list_templates services.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, get_dispatcher
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.repositories.list_template_repo import ListTemplateRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.list_completion_service import ListCompletionService
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.list_signup_service import ListSignupService
from app.services.list_template_service import ListTemplateService
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus


def get_community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _notifier(db: AsyncSession, community_id: uuid.UUID) -> NotificationService:
    return NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        dispatcher=get_dispatcher(),
    )


def get_list_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(get_community_id),
) -> ListService:
    """@brief Build ListService."""
    return ListService(
        ListRepository(db),
        ListMemberRepository(db),
        ListFieldRegistry(),
        community_id,
        db,
        _notifier(db, community_id),
    )


def get_list_item_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(get_community_id),
) -> ListItemService:
    """@brief Build ListItemService."""
    return ListItemService(
        ListItemRepository(db),
        ListRepository(db),
        ListFieldRegistry(),
        _notifier(db, community_id),
    )


def get_list_completion_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(get_community_id),
) -> ListCompletionService:
    """@brief Build ListCompletionService."""
    return ListCompletionService(
        ListItemRepository(db),
        ListRepository(db),
        ListCompletionRepository(db),
        ListFieldRegistry(),
        event_bus,
        _notifier(db, community_id),
        community_id,
    )


def get_list_signup_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(get_community_id),
) -> ListSignupService:
    """@brief Build ListSignupService."""
    return ListSignupService(
        ListItemRepository(db),
        ListSignupRepository(db),
        ListRepository(db),
        ListFieldRegistry(),
        event_bus,
        _notifier(db, community_id),
    )


def get_list_template_service(db: AsyncSession = Depends(get_db)) -> ListTemplateService:
    """@brief Build ListTemplateService."""
    return ListTemplateService(
        ListTemplateRepository(db),
        ListFieldRegistry(),
        ListRepository(db),
        ListItemRepository(db),
    )
