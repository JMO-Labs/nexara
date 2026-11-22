"""
@file chore_service.py
@brief Repeating chores: schedule validation on save and rotation advance.

``advance`` runs under a row lock and only when ``next_due_at <= now``; it
always moves ``next_due_at`` past ``now`` so a second run is a no-op.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.community import Community
from app.models.list import List, ListItem
from app.repositories.chore_repo import ChoreRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_activity_service import ListActivityService
from app.services.notifications.types.list_payloads import item_title

REPEATS = ("daily", "weekly", "monthly")
MAX_ROTATION = 20
COMPLETED_BY_KEY = "_completed_by"


def next_due(prev: datetime, repeat: str) -> datetime:
    """
    @brief Next occurrence after ``prev``; monthly clamps the day (Jan 31 -> Feb 28/29).
    @param prev Previous due time.
    @param repeat One of ``REPEATS``.
    @return The following due time.
    """
    if repeat == "daily":
        return prev + timedelta(days=1)
    if repeat == "weekly":
        return prev + timedelta(days=7)
    if repeat != "monthly":
        raise ValueError(f"bad repeat: {repeat}")
    year, month = (prev.year + 1, 1) if prev.month == 12 else (prev.year, prev.month + 1)
    day = min(prev.day, calendar.monthrange(year, month)[1])
    return prev.replace(year=year, month=month, day=day)


class ChoreService:
    """@brief Save and advance repeating, rotating chores on list items."""

    def __init__(
        self,
        repo: ChoreRepository,
        repo_item: ListItemRepository,
        repo_list: ListRepository,
        repo_assign: ListAssignmentRepository,
        activity: ListActivityService,
        community: Community,
        notification_service: Any | None = None,
    ) -> None:
        """
        @param repo Chore queries.
        @param repo_item Item repository.
        @param repo_list List repository.
        @param repo_assign Assignment repository.
        @param activity Activity recorder.
        @param community The community (feature flag, tenant scope).
        @param notification_service Optional NotificationService.
        """
        self._repo = repo
        self._items = repo_item
        self._lists = repo_list
        self._assign = repo_assign
        self._activity = activity
        self._community = community
        self._cid = community.id
        self._notify = notification_service

    def enabled(self) -> bool:
        """@return Whether the ``chores`` feature is on for this community."""
        from app.core.features import is_enabled

        return is_enabled(self._community, "chores")

    async def _eligible(self, lst: List, ids: set[uuid.UUID]) -> set[uuid.UUID]:
        """@brief Users who are current list members and usable (see repo)."""
        usable = await self._repo.usable_users(ids, lst.owner_id)
        return {u for u in usable if u == lst.owner_id or await self._lists.can_view(lst, u)}

    async def _give(self, lst: List, item: ListItem, user_id: uuid.UUID) -> None:
        """@brief Create a pending assignment, log it and notify the assignee."""
        await self._assign.add(self._cid, lst.id, item.id, user_id, lst.owner_id, "pending")
        title = item_title(item.values)
        await self._activity.record(lst.id, lst.owner_id, "assigned", item.id, title, user_id)
        if self._notify is not None:
            await self._notify.notify(
                user_id,
                "list_assigned",
                {
                    "message": f"Your turn: {title or 'a chore'} on {lst.title}",
                    "list_id": str(lst.id),
                    "item_id": str(item.id),
                    "item_title": title,
                    "event": "assigned",
                },
            )

    async def set_schedule(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        repeat: str | None,
        rotation: list[uuid.UUID],
        now: datetime,
    ) -> ListItem:
        """
        @brief Owner sets repeat + ordered rotation on an item.
        @raises AppError FEATURE_DISABLED / AuthorizationError / ValidationError.
        """
        require_feature(self._community, "chores")
        lst = await self._lists.get_by_id(list_id, self._cid)
        if lst is None or not await self._lists.can_view(lst, user_id):
            raise NotFoundError(_("List not found"))
        if lst.owner_id != user_id:
            raise AuthorizationError(_("Only the owner can edit items"))
        item = await self._items.lock_item_for_update(item_id)
        if item is None or item.list_id != list_id:
            raise NotFoundError(_("List item not found"))
        if repeat is not None and repeat not in REPEATS:
            raise ValidationError(_("Repeat must be daily, weekly or monthly"))
        people = list(dict.fromkeys(rotation))[:MAX_ROTATION] if repeat else []
        if rotation and repeat is None:
            raise ValidationError(_("Choose how often the chore repeats"))
        bad = set(people) - await self._eligible(lst, set(people))
        if bad:
            raise ValidationError(
                _("Rotation people must be members of this list"),
                {"users": sorted(str(b) for b in bad)},
            )
        changes: dict[str, Any] = {"repeat": repeat, "rotation": people}
        if people != list(item.rotation):
            changes["rotation_index"] = 0
        if repeat is None:
            changes["next_due_at"] = None
        elif repeat != item.repeat or item.next_due_at is None:
            changes["next_due_at"] = next_due(now, repeat)
        item = await self._items.update(item, changes)
        if people and await self._assign.get_active(self._cid, item.id) is None:
            await self._give(lst, item, people[0])
        await self._activity.record(
            lst.id, user_id, "item_edited", item.id, item_title(item.values)
        )
        return item

    async def _reopen(self, lst: List, item: ListItem) -> None:
        """@brief Clear completion state so the chore is open for the next turn."""
        if not item.completed:
            return
        values = {k: v for k, v in item.values.items() if k != COMPLETED_BY_KEY}
        await self._repo.clear_completions(item.id)
        await self._items.update(item, {"completed": False, "values": values})
        await self._lists.increment_counters(lst.id, {"completed_count": -1})

    async def advance(self, item: ListItem, now: datetime) -> None:
        """
        @brief Roll a due chore to the next eligible person (item row is locked).

        No-op unless ``next_due_at <= now``. Logs ``missed`` when the current
        assignee did not finish, skips removed/deactivated/memorialized/blocked
        people, reopens the item and moves ``next_due_at`` past ``now``.
        """
        if item.repeat is None or item.next_due_at is None or item.next_due_at > now:
            return
        lst = await self._lists.get_by_id(item.list_id, self._cid)
        if lst is None:
            return
        due = item.next_due_at
        while due <= now:
            due = next_due(due, item.repeat)
        title = item_title(item.values)
        current = await self._assign.get_active(self._cid, item.id)
        if current is not None:
            if not item.completed:
                await self._activity.record(
                    lst.id, None, "missed", item.id, title, current.assignee_id
                )
            await self._assign.remove(current)
        await self._reopen(lst, item)
        changes: dict[str, Any] = {"next_due_at": due}
        order = list(item.rotation)
        ok = await self._eligible(lst, set(order)) if order else set()
        pick: tuple[int, uuid.UUID] | None = None
        for step in range(1, len(order) + 1):
            idx = (item.rotation_index + step) % len(order)
            if order[idx] in ok:
                pick = (idx, order[idx])
                break
        if pick is not None:
            changes["rotation_index"] = pick[0]
        await self._items.update(item, changes)
        if pick is not None:
            await self._give(lst, item, pick[1])

    async def next_assignees(self, items: list[ListItem]) -> dict[uuid.UUID, dict[str, Any]]:
        """@return ``{item_id: user dict}`` of who is next in each item's rotation."""
        nxt = {
            i.id: i.rotation[(i.rotation_index + 1) % len(i.rotation)] for i in items if i.rotation
        }
        users = await self._activity.users(set(nxt.values()))
        return {
            iid: {
                "id": uid,
                "display_name": users[uid].display_name,
                "avatar_url": users[uid].avatar_url,
            }
            for iid, uid in nxt.items()
            if uid in users
        }
