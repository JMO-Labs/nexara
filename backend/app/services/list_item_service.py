"""
@file list_item_service.py
@brief ListItemService: add items, complete/uncomplete, claim/release slots.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.list import ListItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository


class ListItemService:
    """@brief Item operations with transactional claims and counter upkeep."""

    def __init__(
        self,
        repo_list: ListRepository,
        repo_item: ListItemRepository,
        repo_signup: ListSignupRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        """
        @param repo_list List repository (counters).
        @param repo_item Item repository (row locking).
        @param repo_signup Signup repository.
        @param community_id Tenant scope.
        @param session Request-scoped async session.
        """
        self._lists = repo_list
        self._items = repo_item
        self._signups = repo_signup
        self._community_id = community_id
        self._session = session

    async def _get_item(self, item_id: uuid.UUID) -> ListItem:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise NotFoundError(_("List item not found"))
        await self._ensure_in_community(item)
        return item

    async def _ensure_in_community(self, item: ListItem) -> None:
        """@raises NotFoundError If the item's list is outside this community."""
        if await self._lists.get_by_id(item.list_id, self._community_id) is None:
            raise NotFoundError(_("List item not found"))

    async def add_item(
        self,
        list_id: uuid.UUID,
        values: dict[str, Any],
        quantity_needed: int | None = None,
        position: int = 0,
    ) -> ListItem:
        """
        @brief Create an item and bump ``list.item_count``.

        @param list_id Parent list.
        @param values Field values (JSONB).
        @param quantity_needed Slots available for claims; None = unlimited.
        @param position Sort position.
        @return The created item.
        @raises NotFoundError If the list does not exist in this community.
        """
        lst = await self._lists.get_by_id(list_id, self._community_id)
        if lst is None:
            raise NotFoundError(_("List not found"))
        item = await self._items.create(
            ListItem(
                list_id=list_id,
                values=values,
                position=position,
                signup_quantity_needed=quantity_needed,
            )
        )
        await self._lists.increment_counters(list_id, {"item_count": 1})
        return item

    async def complete(self, item_id: uuid.UUID) -> ListItem:
        """@brief Mark an item complete (idempotent) and bump ``completed_count``."""
        return await self._set_completed(item_id, True)

    async def uncomplete(self, item_id: uuid.UUID) -> ListItem:
        """@brief Reopen an item (idempotent) and decrement ``completed_count``."""
        return await self._set_completed(item_id, False)

    async def _set_completed(self, item_id: uuid.UUID, done: bool) -> ListItem:
        item = await self._get_item(item_id)
        if item.completed != done:
            item.completed = done
            await self._session.flush()
            await self._lists.increment_counters(
                item.list_id, {"completed_count": 1 if done else -1}
            )
        return item

    async def claim(
        self, item_id: uuid.UUID, user_id: uuid.UUID, quantity: int = 1, note: str | None = None
    ) -> Any:
        """
        @brief Claim slots on an item under a row lock.

        @param item_id Item to claim.
        @param user_id Claiming user.
        @param quantity Slots requested (>= 1).
        @param note Optional note.
        @return The created ListItemSignup.
        @raises AppError 409 "no slots" when remaining capacity is insufficient.
        """
        if quantity < 1:
            raise AppError("VALIDATION_ERROR", _("Quantity must be at least 1"), 422)
        item = await self._items.lock_item_for_update(item_id)
        if item is None:
            raise NotFoundError(_("List item not found"))
        await self._ensure_in_community(item)
        needed = item.signup_quantity_needed
        if needed is not None:
            claimed = await self._signups.sum_claimed(item_id)
            if needed - claimed < quantity:
                raise AppError("NO_SLOTS", _("There are no slots left on this item"), 409)
        signup = await self._signups.create_claim(item_id, user_id, quantity, note)
        await self._lists.increment_counters(item.list_id, {"signup_count": 1})
        return signup

    async def release(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        @brief Remove the user's claim and decrement ``signup_count``.

        @raises NotFoundError If the user holds no claim on the item.
        """
        item = await self._items.lock_item_for_update(item_id)
        if item is None:
            raise NotFoundError(_("List item not found"))
        await self._ensure_in_community(item)
        if not await self._signups.delete_claim(item_id, user_id):
            raise NotFoundError(_("Claim not found"))
        await self._lists.increment_counters(item.list_id, {"signup_count": -1})
