"""
@file list_assignments.py
@brief Item take/assign/respond/release routes and the list activity feed.

Mounted under ``/lists``. Errors use the standard envelope.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.core.list_dependencies import (
    get_list_activity_service,
    get_list_assignment_service,
)
from app.models.list import ListItem
from app.models.user import User
from app.schemas.list import AssigneeOut, ListItemOut, Pagination
from app.schemas.list_assignment import ActivityOut, ActivityPage, AssignBody
from app.services.list_activity_service import ListActivityService
from app.services.list_assignment_service import ListAssignmentService

router = APIRouter(prefix="/lists", tags=["list-assignments"])


def _admin(user: User) -> bool:
    return user.role in ("admin", "owner")


def item_out(
    item: ListItem, info: dict[str, Any] | None, nxt: dict[str, Any] | None = None
) -> ListItemOut:
    """@brief Serialise an item with its (optional) assignment and next-in-rotation info."""
    out = ListItemOut.model_validate(item)
    if nxt:
        out.next_assignee = AssigneeOut.model_validate(nxt)
    if info:
        out.assignee = AssigneeOut.model_validate(info["assignee"])
        out.assignment_status = info["status"]
    return out


async def _described(svc: ListAssignmentService, list_id: uuid.UUID, item: ListItem) -> ListItemOut:
    info = await svc.describe(list_id, [item.id])
    return item_out(item, info.get(item.id))


@router.post("/{list_id}/items/{item_id}/take", response_model=ListItemOut)
async def take_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief Take an open item (accepted immediately)."""
    return await _described(svc, list_id, await svc.take(list_id, item_id, user.id))


@router.post("/{list_id}/items/{item_id}/assign", response_model=ListItemOut)
async def assign_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    body: AssignBody,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief Owner/editor assigns an item to a member (pending until accepted)."""
    item = await svc.assign(list_id, item_id, user.id, body.user_id, _admin(user))
    return await _described(svc, list_id, item)


@router.post("/{list_id}/items/{item_id}/assignment/accept", response_model=ListItemOut)
async def accept_assignment(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief The pending assignee accepts."""
    return await _described(svc, list_id, await svc.respond(list_id, item_id, user.id, True))


@router.post("/{list_id}/items/{item_id}/assignment/decline", response_model=ListItemOut)
async def decline_assignment(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief The pending assignee declines; the item returns to open."""
    return await _described(svc, list_id, await svc.respond(list_id, item_id, user.id, False))


@router.post("/{list_id}/items/{item_id}/release", response_model=ListItemOut)
async def release_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief The assignee gives back an accepted item."""
    return await _described(svc, list_id, await svc.release(list_id, item_id, user.id))


@router.delete("/{list_id}/items/{item_id}/assignment", response_model=ListItemOut)
async def unassign_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ListAssignmentService = Depends(get_list_assignment_service),
) -> ListItemOut:
    """@brief Owner/editor clears the assignment."""
    item = await svc.unassign(list_id, item_id, user.id, _admin(user))
    return await _described(svc, list_id, item)


@router.get("/{list_id}/activity", response_model=ActivityPage)
async def list_activity(
    list_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    svc: ListActivityService = Depends(get_list_activity_service),
) -> ActivityPage:
    """@brief Newest-first keyset page of the list's activity log."""
    rows, users, nxt = await svc.page(list_id, user.id, cursor, limit)

    def ref(uid: uuid.UUID | None) -> AssigneeOut | None:
        if uid is None:
            return None
        u = users.get(uid)
        return AssigneeOut(
            id=uid, display_name=u.display_name if u else "", avatar_url=u.avatar_url if u else None
        )

    entries = [
        ActivityOut(
            id=r.id,
            action=r.action,
            actor=ref(r.actor_id),
            item_id=r.item_id,
            item_title=r.item_title,
            target_user=ref(r.target_user_id),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ActivityPage(
        activity=entries, pagination=Pagination(cursor=nxt, has_more=nxt is not None)
    )
