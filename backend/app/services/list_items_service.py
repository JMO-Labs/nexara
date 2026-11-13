"""
@file list_items_service.py
@brief Service for list items: validation, hot-column projection, counters.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.list import List, ListItem, ListItemCompletion, ListMember
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry

HOT_COLUMNS = ("due_at", "lat", "lon", "signup_quantity_needed")


class ListItemService:
    """@brief Item CRUD with schema validation and denormalised counters."""

    def __init__(
        self,
        repo_item: ListItemRepository,
        repo_list: ListRepository,
        field_registry: ListFieldRegistry,
    ) -> None:
        """
        @param repo_item Item repository.
        @param repo_list List repository.
        @param field_registry Field type registry.
        """
        self._items = repo_item
        self._lists = repo_list
        self._registry = field_registry

    async def _get_list(self, list_id: uuid.UUID) -> List:
        lst = await self._lists.get_by_id(list_id)
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
            stmt = select(ListMember.user_id).where(
                ListMember.list_id == lst.id, ListMember.user_id == viewer_id
            )
            res = await self._lists.session.execute(stmt)
            return res.first() is not None
        return False

    async def _get_item(self, item_id: uuid.UUID) -> tuple[ListItem, List]:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Item not found")
        return item, await self._get_list(item.list_id)

    async def list_items(
        self,
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
        lst = await self._get_list(list_id)
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
        for key, field in fields.items():
            try:
                out[key] = self._registry.validate_value(
                    field["type_key"], values.get(key), field.get("config", {})
                )
            except (ValueError, FieldTypeNotFound) as exc:
                raise ValidationError(f"Invalid value for {key}", {"field": key}) from exc
        return out

    def _project_item(self, lst: List, item: ListItem) -> dict[str, Any]:
        """@brief Merge hot columns projected by each field in the schema."""
        cols: dict[str, Any] = {}
        for field in lst.field_schema:
            projected = self._registry.project_columns(
                field["type_key"], item.values.get(field["key"]), field.get("config", {})
            )
            cols.update({k: v for k, v in projected.items() if k in HOT_COLUMNS})
        return cols

    def _apply_projection(self, lst: List, item: ListItem) -> None:
        for k, v in self._project_item(lst, item).items():
            setattr(item, k, v)

    async def create(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        values: dict[str, Any],
        position: int = 0,
    ) -> ListItem:
        """
        @brief Validate, project and persist an item; bump ``item_count``.

        @raises ValidationError On invalid values.
        """
        lst = await self._get_list(list_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can add items")
        item = ListItem(
            list_id=list_id, position=position, values=self._validate_values(lst, values)
        )
        self._apply_projection(lst, item)
        item = await self._items.create(item)
        await self._lists.increment_counters(list_id, {"item_count": 1})
        return item

    async def update(
        self, item_id: uuid.UUID, user_id: uuid.UUID, values: dict[str, Any]
    ) -> ListItem:
        """@brief Merge, re-validate and re-project item values."""
        item, lst = await self._get_item(item_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can edit items")
        merged = {**item.values, **values}
        item.values = self._validate_values(lst, merged)
        self._apply_projection(lst, item)
        cols = {k: getattr(item, k) for k in HOT_COLUMNS if hasattr(item, k)}
        return await self._items.update(item, {"values": item.values, **cols})

    async def delete(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Soft-delete an item and decrement counters."""
        item, lst = await self._get_item(item_id)
        if lst.owner_id != user_id:
            raise AuthorizationError("Only the owner can delete items")
        await self._items.soft_delete(item)
        delta = {"item_count": -1}
        if item.completed:
            delta["completed_count"] = -1
        await self._lists.increment_counters(lst.id, delta)

    async def _sync_item_counters(self, lst: List) -> None:
        """@brief Recompute item_count/completed_count from the DB."""
        live = ListItem.list_id == lst.id, ListItem.deleted_at.is_(None)
        done = func.count(ListItem.id).filter(ListItem.completed.is_(True))
        per_user = (
            select(func.count(func.distinct(ListItemCompletion.item_id)))
            .join(ListItem, ListItem.id == ListItemCompletion.item_id)
            .where(*live, ListItem.completed.is_(False))
            .scalar_subquery()
        )
        stmt = select(func.count(ListItem.id), done + per_user).where(*live)
        total, completed = (await self._lists.session.execute(stmt)).one()
        await self._lists.update(lst, {"item_count": total, "completed_count": completed})
