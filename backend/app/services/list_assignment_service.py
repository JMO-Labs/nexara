"""
@file list_assignment_service.py
@brief Take / assign / respond / release / unassign for list items.

One active (pending or accepted) assignee per item, serialised by a
``SELECT ... FOR UPDATE`` on the item row. Every transition is logged to the
list activity log.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.list import List, ListItem
from app.models.list_assignment import ListItemAssignment
from app.models.user import User
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.services.list_activity_service import ListActivityService
from app.services.notifications.types.list_payloads import item_title


class ListAssignmentService:
    """@brief Business logic for item assignments."""

    def __init__(
        self,
        repo_assign: ListAssignmentRepository,
        repo_item: ListItemRepository,
        repo_list: ListRepository,
        repo_member: ListMemberRepository,
        activity: ListActivityService,
        community_id: uuid.UUID,
        notification_service: Any | None = None,
    ) -> None:
        """
        @param repo_assign Assignment repository.
        @param repo_item Item repository (row lock).
        @param repo_list List repository (visibility).
        @param repo_member List member repository (editor roles).
        @param activity Activity recorder.
        @param community_id Tenant scope.
        @param notification_service Optional NotificationService.
        """
        self._assign = repo_assign
        self._items = repo_item
        self._lists = repo_list
        self._members = repo_member
        self._activity = activity
        self._community_id = community_id
        self._notify = notification_service

    async def _load(
        self, list_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[List, ListItem]:
        """@brief Lock the item; 404 unless the caller can view its list."""
        lst = await self._lists.get_by_id(list_id, self._community_id)
        if lst is None or not await self._lists.can_view(lst, user_id):
            raise NotFoundError(_("List not found"))
        item = await self._items.lock_item_for_update(item_id)
        if item is None or item.list_id != list_id:
            raise NotFoundError(_("List item not found"))
        return lst, item

    async def can_edit(self, lst: List, user_id: uuid.UUID, is_admin: bool = False) -> bool:
        """@brief Owner, global admin, or list member with role ``admin``."""
        if lst.owner_id == user_id or is_admin:
            return True
        member = await self._members.get_member(lst.id, user_id)
        return member is not None and member.role == "admin"

    async def _require_editor(self, lst: List, user_id: uuid.UUID, is_admin: bool) -> None:
        if not await self.can_edit(lst, user_id, is_admin):
            raise AuthorizationError(_("Only list owners and editors can do this"))

    async def _log(
        self,
        lst: List,
        item: ListItem,
        actor_id: uuid.UUID,
        action: str,
        target: uuid.UUID | None = None,
    ) -> None:
        await self._activity.record(
            lst.id, actor_id, action, item.id, item_title(item.values), target
        )

    async def _tell(
        self, to: uuid.UUID, actor_id: uuid.UUID, lst: List, item: ListItem, event: str
    ) -> None:
        """@brief Notify ``to`` (never the actor) about an assignment event."""
        if self._notify is None or to == actor_id:
            return
        title = item_title(item.values)
        text = {
            "assigned": "assigned you",
            "accepted": "accepted",
            "declined": "declined",
        }[event]
        await self._notify.notify(
            to,
            "list_assigned",
            {
                "message": f"{text.capitalize()}: {title or 'an item'} on {lst.title}",
                "list_id": str(lst.id),
                "item_id": str(item.id),
                "item_title": title,
                "event": event,
            },
            actor_id=actor_id,
        )

    async def take(self, list_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID) -> ListItem:
        """
        @brief Assign an open item to the caller, accepted immediately.

        @raises AppError 409 When the item already has an active assignee.
        """
        lst, item = await self._load(list_id, item_id, user_id)
        if await self._assign.get_active(self._community_id, item_id) is not None:
            raise AppError("ALREADY_ASSIGNED", _("This item is already taken"), 409)
        await self._assign.add(self._community_id, list_id, item_id, user_id, user_id, "accepted")
        await self._log(lst, item, user_id, "taken")
        return item

    async def assign(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        actor_id: uuid.UUID,
        assignee_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ListItem:
        """
        @brief Owner/editor assigns the item to a member who can see the list.

        Replaces any existing active assignment. Assigning oneself is accepted
        at once; anyone else gets a pending request and a notification.

        @raises AuthorizationError When the caller is not owner/editor.
        @raises ValidationError When the assignee cannot view the list.
        """
        lst, item = await self._load(list_id, item_id, actor_id)
        await self._require_editor(lst, actor_id, is_admin)
        users = await self._activity.users({assignee_id})
        assignee: User | None = users.get(assignee_id)
        if (
            assignee is None
            or not assignee.is_active
            or not await self._lists.can_view(lst, assignee_id)
        ):
            raise ValidationError(_("That user cannot see this list"))
        current = await self._assign.get_active(self._community_id, item_id)
        if current is not None:
            await self._assign.remove(current)
        status = "accepted" if assignee_id == actor_id else "pending"
        await self._assign.add(self._community_id, list_id, item_id, assignee_id, actor_id, status)
        await self._log(lst, item, actor_id, "assigned", assignee_id)
        await self._tell(assignee_id, actor_id, lst, item, "assigned")
        return item

    async def _pending_for(
        self, item_id: uuid.UUID, user_id: uuid.UUID, status: str
    ) -> ListItemAssignment:
        row = await self._assign.get_active(self._community_id, item_id)
        if row is None or row.assignee_id != user_id:
            raise NotFoundError(_("Assignment not found"))
        if row.status != status:
            raise AppError("INVALID_STATE", _("Assignment is not %s") % status, 409)
        return row

    async def respond(
        self, list_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID, accept: bool
    ) -> ListItem:
        """
        @brief The pending assignee accepts or declines (decline reopens the item).

        @raises NotFoundError When the caller is not the active assignee.
        @raises AppError 409 When the assignment is not pending.
        """
        lst, item = await self._load(list_id, item_id, user_id)
        row = await self._pending_for(item_id, user_id, "pending")
        await self._assign.set_status(row, "accepted" if accept else "declined")
        action = "accepted" if accept else "declined"
        await self._log(lst, item, user_id, action)
        await self._tell(row.assigned_by, user_id, lst, item, action)
        return item

    async def release(self, list_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID) -> ListItem:
        """@brief The assignee gives back an accepted item (returns it to open)."""
        lst, item = await self._load(list_id, item_id, user_id)
        row = await self._pending_for(item_id, user_id, "accepted")
        await self._assign.remove(row)
        await self._log(lst, item, user_id, "released")
        return item

    async def unassign(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        actor_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ListItem:
        """
        @brief Owner/editor clears the active assignment.

        @raises AuthorizationError When the caller is not owner/editor.
        @raises NotFoundError When the item has no active assignment.
        """
        lst, item = await self._load(list_id, item_id, actor_id)
        await self._require_editor(lst, actor_id, is_admin)
        row = await self._assign.get_active(self._community_id, item_id)
        if row is None:
            raise NotFoundError(_("Assignment not found"))
        await self._assign.remove(row)
        await self._log(lst, item, actor_id, "unassigned", row.assignee_id)
        return item

    async def describe(
        self, list_id: uuid.UUID, item_ids: list[uuid.UUID] | None = None
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        @brief Assignee info per item for response enrichment.

        @param list_id Parent list.
        @param item_ids Optional filter; ``None`` returns every assigned item.
        @return ``{item_id: {"assignee": {...}, "status": str}}``.
        """
        rows = await self._assign.active_for_list(self._community_id, list_id)
        if item_ids is not None:
            wanted = set(item_ids)
            rows = {k: v for k, v in rows.items() if k in wanted}
        users = await self._activity.users({r.assignee_id for r in rows.values()})
        out: dict[uuid.UUID, dict[str, Any]] = {}
        for item_id, row in rows.items():
            user = users.get(row.assignee_id)
            out[item_id] = {
                "assignee": {
                    "id": row.assignee_id,
                    "display_name": user.display_name if user else "",
                    "avatar_url": user.avatar_url if user else None,
                },
                "status": row.status,
            }
        return out
