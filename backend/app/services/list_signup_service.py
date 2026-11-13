"""
@file list_signup_service.py
@brief Claim/release of list-item signups, serialised by a row lock.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.list import ListItem, ListItemSignup
from app.services.realtime.events import EventType, RealtimeEvent, UserTarget


class ListSignupService:
    """
    @brief Business logic for item signups.

    ``ListItem.signup_quantity_needed`` holds the *remaining* slots: claims
    decrement it and releases restore it, all under ``SELECT ... FOR UPDATE``.
    """

    def __init__(
        self,
        repo_item: Any,
        repo_signup: Any,
        repo_list: Any,
        field_registry: Any,
        event_bus: Any,
        notification_service: Any,
    ) -> None:
        """
        @param repo_item ListItemRepository.
        @param repo_signup ListSignupRepository.
        @param repo_list ListRepository (counters, owner lookup).
        @param field_registry ListFieldRegistry.
        @param event_bus EventBus.
        @param notification_service NotificationService.
        """
        self._items = repo_item
        self._signups = repo_signup
        self._lists = repo_list
        self._registry = field_registry
        self._bus = event_bus
        self._notify = notification_service

    async def _locked_item(self, item_id: uuid.UUID, session: AsyncSession) -> ListItem:
        item = await self._items.lock_item_for_update(item_id, session)
        if item is None:
            raise NotFoundError("List item not found")
        return item

    async def _emit(self, user_id: uuid.UUID, action: str, item: ListItem, qty: int) -> None:
        await self._bus.emit(
            RealtimeEvent(
                type=EventType.FEED_UPDATE,
                target=UserTarget(user_id=user_id),
                payload={
                    "event": f"list_signup_{action}",
                    "list_id": str(item.list_id),
                    "item_id": str(item.id),
                    "user_id": str(user_id),
                    "quantity": qty,
                },
            )
        )

    async def claim_signup(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        quantity: int,
        session: AsyncSession,
        note: str | None = None,
    ) -> ListItemSignup:
        """
        @brief Claim ``quantity`` slots on an item under a row lock.

        @param item_id Target item.
        @param user_id Claiming user.
        @param quantity Slots to claim (>= 1).
        @param session Transaction session holding the lock.
        @param note Optional note.
        @return The created signup.
        @raises AppError On invalid quantity, duplicate claim or no free slots.
        @raises NotFoundError If the item does not exist.
        """
        if quantity < 1:
            raise AppError("VALIDATION_ERROR", "Quantity must be at least 1", 422)
        item = await self._locked_item(item_id, session)
        remaining = item.signup_quantity_needed
        if remaining is None:
            raise AppError("SIGNUP_NOT_ENABLED", "Item does not accept signups", 409)
        if any(c.user_id == user_id for c in await self._signups.list_for_item(item_id)):
            raise AppError("ALREADY_CLAIMED", "Already signed up for this item", 409)
        if remaining <= 0 or quantity > remaining:
            raise AppError("NO_SLOTS", "Not enough open slots", 409, {"remaining": remaining})
        claim = await self._signups.create_claim(item_id, user_id, quantity, note)
        item.signup_quantity_needed = remaining - quantity
        await session.flush()
        lst = await self._lists.get_by_id(item.list_id)
        await self._lists.increment_counters(item.list_id, {"signup_count": 1})
        await self._emit(user_id, "claimed", item, quantity)
        if lst is not None and lst.owner_id != user_id:
            await self._notify.notify(
                lst.owner_id,
                "system",
                {"message": "Someone signed up on your list", "target_id": str(item_id)},
                actor_id=user_id,
            )
        return claim

    async def release_signup(
        self, item_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
    ) -> None:
        """
        @brief Delete a user's claim and restore the slots.

        @raises NotFoundError If the item or the claim does not exist.
        """
        item = await self._locked_item(item_id, session)
        claim = next(
            (c for c in await self._signups.list_for_item(item_id) if c.user_id == user_id),
            None,
        )
        if claim is None:
            raise NotFoundError("Signup not found")
        qty = claim.quantity
        await self._signups.delete_claim(item_id, user_id)
        item.signup_quantity_needed = (item.signup_quantity_needed or 0) + qty
        await session.flush()
        await self._lists.increment_counters(item.list_id, {"signup_count": -1})
        await self._emit(user_id, "released", item, qty)

    async def get_signups_for_item(self, item_id: uuid.UUID) -> list[ListItemSignup]:
        """@brief All claims on an item, oldest first."""
        return list(await self._signups.list_for_item(item_id))

    async def get_signup(self, item_id: uuid.UUID, user_id: uuid.UUID) -> ListItemSignup | None:
        """@brief A user's claim on an item, or None."""
        claims = await self.get_signups_for_item(item_id)
        return next((c for c in claims if c.user_id == user_id), None)
