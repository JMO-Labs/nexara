"""
@file list_signup_repo.py
@brief Repository for item signups (claims).
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult

from app.models.list import ListItemSignup
from app.repositories.base import BaseRepository


class ListSignupRepository(BaseRepository[ListItemSignup]):
    """@brief Async repo for ListItemSignup rows.

    @note Composite PK, no ``id``: inherited ``get_by_id`` is unusable; use
        ``list_for_item``/``create_claim``/``delete_claim``.
    """

    model = ListItemSignup

    async def sum_claimed(self, item_id: uuid.UUID) -> int:
        """@brief Total quantity claimed on an item (0 when none)."""
        stmt = select(func.coalesce(func.sum(ListItemSignup.quantity), 0)).where(
            ListItemSignup.item_id == item_id
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def create_claim(
        self, item_id: uuid.UUID, user_id: uuid.UUID, quantity: int = 1, note: str | None = None
    ) -> ListItemSignup:
        """@brief Persist a claim for a user on an item."""
        return await self.create(
            ListItemSignup(item_id=item_id, user_id=user_id, quantity=quantity, note=note)
        )

    async def delete_claim(self, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Remove a user's claim. @return True if a row was deleted."""
        stmt = delete(ListItemSignup).where(
            ListItemSignup.item_id == item_id, ListItemSignup.user_id == user_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (cast(CursorResult[Any], result).rowcount or 0) > 0

    async def list_for_item(self, item_id: uuid.UUID) -> list[ListItemSignup]:
        """@brief All claims on an item, oldest first."""
        stmt = (
            self._base_query()
            .where(ListItemSignup.item_id == item_id)
            .order_by(ListItemSignup.claimed_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())
