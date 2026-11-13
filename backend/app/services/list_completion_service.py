"""
@file list_completion_service.py
@brief Complete/uncomplete list items, branching on checkbox completion_mode.

Shared mode keeps one flag on the item (``completed`` + ``_completed_by``).
Per-user mode stores a ``list_item_completion`` row per user; ``item.completed``
means "at least one user completed" and is cleared when the last row is removed.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, NotFoundError
from app.models.list import List, ListItem
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_field_registry import ListFieldRegistry
from app.services.realtime.event_bus import EventBus
from app.services.realtime.events import CommunityTarget, EventType, RealtimeEvent, UserTarget

COMPLETED_BY_KEY = "_completed_by"


class ListCompletionService:
    """@brief Branching completion logic for list items."""

    def __init__(
        self,
        item_repo: ListItemRepository,
        list_repo: ListRepository,
        completion_repo: ListCompletionRepository,
        field_registry: ListFieldRegistry,
        event_bus: EventBus,
        notification_service: Any,
        community_id: uuid.UUID,
    ) -> None:
        """@brief Wire repos, registry, event bus and notifier."""
        self._items = item_repo
        self._lists = list_repo
        self._completions = completion_repo
        self._registry = field_registry
        self._bus = event_bus
        self._notify = notification_service
        self._community_id = community_id

    def _get_completion_mode(self, schema: list[dict[str, Any]], field_key: str | None) -> str:
        """
        @brief Extract completion_mode from the completion field's config.

        @param schema List field_schema.
        @param field_key Field key; defaults to the first checkbox field.
        @return "shared" (default) or "per_user".
        @throws AppError FIELD_NOT_FOUND if field_key matches no checkbox field.
        """
        checkboxes = [f for f in schema if f.get("type") == "checkbox"]
        if field_key is None:
            field = checkboxes[0] if checkboxes else None
        else:
            field = next((f for f in checkboxes if f.get("key") == field_key), None)
            if field is None:
                raise AppError(
                    code="FIELD_NOT_FOUND",
                    message=f"Checkbox field not found: {field_key}",
                    status_code=422,
                )
        if field is None:
            return "shared"
        mode = (field.get("config") or {}).get("completion_mode")
        return "per_user" if mode == "per_user" else "shared"

    async def _load(
        self, item_id: uuid.UUID, user_id: uuid.UUID, field_key: str | None
    ) -> tuple[ListItem, List, str]:
        item = await self._items.lock_item_for_update(item_id)
        lst = await self._lists.get_by_id(item.list_id, self._community_id) if item else None
        if item is None or lst is None:
            raise NotFoundError("List item not found")
        if not await self._lists.can_view(lst, user_id):
            raise NotFoundError("List item not found")
        return item, lst, self._get_completion_mode(lst.field_schema, field_key)

    async def complete_item(
        self, item_id: uuid.UUID, user_id: uuid.UUID, field_key: str | None = None
    ) -> ListItem:
        """
        @brief Mark an item complete for the user (or for everyone in shared mode).

        @param item_id Item UUID.
        @param user_id Acting user.
        @param field_key Optional checkbox field key.
        @return The item.
        """
        item, lst, mode = await self._load(item_id, user_id, field_key)
        was_completed = item.completed
        if mode == "shared":
            if was_completed:
                return item
            values = {**item.values, COMPLETED_BY_KEY: str(user_id)}
            await self._items.update(item, {"completed": True, "values": values})
        else:
            if await self._completions.get_completion(item.id, user_id):
                return item
            await self._completions.create_completion(item.id, user_id)
            if not was_completed:
                await self._items.update(item, {"completed": True})
        if not was_completed:
            await self._lists.increment_counters(lst.id, {"completed_count": 1})
        await self._emit("list.completed", lst, item, user_id, mode)
        if lst.owner_id != user_id:
            await self._notify.notify(
                lst.owner_id,
                "list_completed",
                {
                    "list_id": str(lst.id),
                    "list_title": lst.title,
                    "item_id": str(item.id),
                    "completion_mode": mode,
                },
                actor_id=user_id,
            )
        return item

    async def uncomplete_item(
        self, item_id: uuid.UUID, user_id: uuid.UUID, field_key: str | None = None
    ) -> ListItem:
        """
        @brief Reverse :meth:`complete_item` for the given mode.

        @param item_id Item UUID.
        @param user_id Acting user.
        @param field_key Optional checkbox field key.
        @return The item.
        """
        item, lst, mode = await self._load(item_id, user_id, field_key)
        if mode == "shared":
            if not item.completed:
                return item
            values = {k: v for k, v in item.values.items() if k != COMPLETED_BY_KEY}
            await self._items.update(item, {"completed": False, "values": values})
        else:
            if not await self._completions.delete_completion(item.id, user_id):
                return item
            if await self._completions.count_for_item(item.id) > 0:
                await self._emit("list.uncompleted", lst, item, user_id, mode)
                return item
            await self._items.update(item, {"completed": False})
        await self._lists.increment_counters(lst.id, {"completed_count": -1})
        await self._emit("list.uncompleted", lst, item, user_id, mode)
        return item

    async def _emit(
        self, name: str, lst: List, item: ListItem, user_id: uuid.UUID, mode: str
    ) -> None:
        payload = {
            "event": name,
            "list_id": str(lst.id),
            "item_id": str(item.id),
            "user_id": str(user_id),
            "completion_mode": mode,
            "completed": item.completed,
        }
        if lst.visibility == "community":
            targets: list[CommunityTarget | UserTarget] = [
                CommunityTarget(community_id=self._community_id)
            ]
        else:
            audience = await self._lists.audience_ids(lst) | {lst.owner_id, user_id}
            targets = [UserTarget(user_id=uid) for uid in audience]
        for target in targets:
            await self._bus.emit(
                RealtimeEvent(type=EventType.FEED_UPDATE, target=target, payload=payload)
            )
