"""
@file list_items_service.py
@brief Service for list items: validation, hot-column projection, counters.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.list import List, ListItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_field_registry import FieldTypeNotFoundError, ListFieldRegistry
from app.services.notifications.types.list_payloads import item_title

HOT_COLUMNS = ("due_at", "lat", "lon", "signup_quantity_needed")


class ListItemService:
    """@brief Item CRUD with schema validation and denormalised counters."""

    def __init__(
        self,
        repo_item: ListItemRepository,
        repo_list: ListRepository,
        field_registry: ListFieldRegistry,
        notification_service: Any | None = None,
    ) -> None:
        """
        @param repo_item Item repository.
        @param repo_list List repository.
        @param field_registry Field type registry.
        @param notification_service Optional NotificationService for list_item.
        """
        self._items = repo_item
        self._lists = repo_list
        self._registry = field_registry
        self._notify = notification_service

    async def _notify_item_added(self, lst: List, item: ListItem, adder_id: uuid.UUID) -> None:
        """@brief Send ``list_item`` to the owner and list audience, minus the adder."""
        if self._notify is None:
            return
        recipients = (await self._lists.audience_ids(lst)) | {lst.owner_id}
        recipients.discard(adder_id)
        title = item_title(item.values)
        payload = {
            "message": f"New item on {lst.title}: {title}" if title else f"New item on {lst.title}",
            "list_id": str(lst.id),
            "item_id": str(item.id),
            "item_title": title,
            "adder_id": str(adder_id),
        }
        for uid in sorted(recipients, key=str):
            await self._notify.notify(uid, "list_item", payload, actor_id=adder_id)

    async def _get_list(self, community_id: uuid.UUID, list_id: uuid.UUID) -> List:
        lst = await self._lists.get_by_id(list_id, community_id)
        if lst is None:
            raise NotFoundError("List not found")
        return lst

    async def _can_view(
        self, lst: List, viewer_id: uuid.UUID, subgroup_ids: list[uuid.UUID] | None
    ) -> bool:
        if lst.visibility == "community":
            return True
        if lst.owner_id == viewer_id:
            return True
        if lst.visibility == "subgroup":
            return lst.subgroup_id is not None and lst.subgroup_id in (subgroup_ids or [])
        if lst.visibility == "members":
            return await self._lists.is_member(lst.id, viewer_id)
        return False

    async def _get_item(self, community_id: uuid.UUID, item_id: uuid.UUID) -> tuple[ListItem, List]:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Item not found")
        return item, await self._get_list(community_id, item.list_id)

    async def list_items(
        self,
        community_id: uuid.UUID,
        list_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "position",
        subgroup_ids: list[uuid.UUID] | None = None,
    ) -> tuple[list[ListItem], str | None]:
        """
        @brief Keyset-paginate items of a list the viewer may see.

        @return (items, next_cursor).
        @raises NotFoundError / AuthorizationError / ValidationError.
        """
        lst = await self._get_list(community_id, list_id)
        if not await self._can_view(lst, viewer_id, subgroup_ids):
            raise AuthorizationError("Cannot view this list")
        try:
            return await self._items.list_items_keyset(list_id, cursor, limit, sort_by)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def _validate_values(self, lst: List, values: dict[str, Any]) -> dict[str, Any]:
        fields = {f["key"]: f for f in lst.field_schema}
        unknown = set(values) - set(fields)
        if unknown:
            raise ValidationError("Unknown fields", {"fields": sorted(unknown)})
        out: dict[str, Any] = {}
        for key in values:
            field = fields[key]
            try:
                out[key] = self._registry.validate_value(
                    field["type_key"], values[key], field.get("config", {})
                )
            except (ValueError, FieldTypeNotFoundError) as exc:
                raise ValidationError(f"Invalid value for {key}", {"field": key}) from exc
        return out

    def _project_item(self, lst: List, item: ListItem) -> dict[str, Any]:
        """@brief Merge hot columns projected by each field in the schema."""
        cols: dict[str, Any] = dict.fromkeys(HOT_COLUMNS)
        for field in lst.field_schema:
            value = item.values.get(field["key"])
            if value is None:
                continue
            projected = self._registry.project_columns(
                field["type_key"], value, field.get("config", {})
            )
            cols.update({k: v for k, v in projected.items() if k in HOT_COLUMNS})
        return cols

    def _apply_projection(self, lst: List, item: ListItem) -> None:
        for k, v in self._project_item(lst, item).items():
            setattr(item, k, v)

    async def create(
        self,
        community_id: uuid.UUID,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        values: dict[str, Any],
        position: int = 0,
    ) -> ListItem:
        """
        @brief Validate, project and persist an item; bump ``item_count``.

        @raises ValidationError On invalid values.
        """
        lst = await self._get_list(community_id, list_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can add items")
        item = ListItem(
            list_id=list_id, position=position, values=self._validate_values(lst, values)
        )
        self._apply_projection(lst, item)
        item = await self._items.create(item)
        await self._lists.increment_counters(list_id, {"item_count": 1})
        await self._notify_item_added(lst, item, user_id)
        return item

    async def update(
        self,
        community_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        values: dict[str, Any],
    ) -> ListItem:
        """@brief Merge, re-validate and re-project item values."""
        item, lst = await self._get_item(community_id, item_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can edit items")
        merged = {k: v for k, v in {**item.values, **values}.items() if v is not None}
        item.values = self._validate_values(lst, merged)
        return await self._items.update(
            item, {"values": item.values, **self._project_item(lst, item)}
        )

    async def delete(self, community_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Soft-delete an item and decrement counters."""
        item, lst = await self._get_item(community_id, item_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can delete items")
        await self._items.soft_delete(item)
        delta = {"item_count": -1}
        if item.completed:
            delta["completed_count"] = -1
        await self._lists.increment_counters(lst.id, delta)

    async def sync_item_counters(self, lst: List) -> None:
        """
        @brief Recompute item_count/completed_count from the DB.

        @note Not yet wired to a maintenance task (follow-up ticket).
        """
        total, completed = await self._items.count_live_and_completed(lst.id)
        await self._lists.update(lst, {"item_count": total, "completed_count": completed})
