"""
@file list_chores.py
@brief Route to set a list item's repeat and rotation (feature ``chores``).

Mounted under ``/lists``. Errors use the standard envelope.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.list_assignments import item_out
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.core.exceptions import NotFoundError
from app.core.list_dependencies import get_community_id, get_list_activity_service
from app.models.user import User
from app.repositories.chore_repo import ChoreRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.list import ChoreScheduleIn, ListItemOut
from app.services.chore_service import ChoreService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/lists", tags=["list-chores"])


async def get_chore_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(get_community_id),
) -> ChoreService:
    """@brief Build ChoreService for the current community."""
    community = await CommunityRepository(db).get(community_id)
    if community is None:
        raise NotFoundError("Community not found")
    notifier = NotificationService(
        NotificationRepository(db),
        SettingsRepository(db),
        community_id,
        dispatcher=get_dispatcher(),
    )
    return ChoreService(
        ChoreRepository(db),
        ListItemRepository(db),
        ListRepository(db),
        ListAssignmentRepository(db),
        get_list_activity_service(db, community_id),
        community,
        notifier,
    )


@router.put("/{list_id}/items/{item_id}/chore", response_model=ListItemOut)
async def set_chore(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ChoreScheduleIn,
    user: User = Depends(get_current_user),
    svc: ChoreService = Depends(get_chore_service),
) -> ListItemOut:
    """@brief Owner sets (or clears) an item's repeat and ordered rotation."""
    item = await svc.set_schedule(
        list_id, item_id, user.id, body.repeat, body.rotation, datetime.now(UTC)
    )
    nxt = await svc.next_assignees([item])
    return item_out(item, None, nxt.get(item.id))
