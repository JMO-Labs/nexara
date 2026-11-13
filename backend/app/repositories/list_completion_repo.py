"""
@file list_completion_repo.py
@brief Repository for per-user item completions.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult

from app.models.list import ListItemCompletion
from app.repositories.base import BaseRepository


class ListCompletionRepository(BaseRepository[ListItemCompletion]):
    """@brief Async repo for ListItemCompletion rows."""

    model = ListItemCompletion

    async def get_completion(
        self, item_id: uuid.UUID, user_id: uuid.UUID
    ) -> ListItemCompletion | None:
        """@brief Fetch a user's completion of an item."""
        stmt = self._base_query().where(
            ListItemCompletion.item_id == item_id, ListItemCompletion.user_id == user_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_completion(self, item_id: uuid.UUID, user_id: uuid.UUID) -> ListItemCompletion:
        """@brief Mark an item complete for a user."""
        return await self.create(ListItemCompletion(item_id=item_id, user_id=user_id))

    async def delete_completion(self, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Remove a completion. @return True if a row was deleted."""
        stmt = delete(ListItemCompletion).where(
            ListItemCompletion.item_id == item_id, ListItemCompletion.user_id == user_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (cast(CursorResult[Any], result).rowcount or 0) > 0

    async def count_for_item(self, item_id: uuid.UUID) -> int:
        """@brief Count users who completed an item."""
        stmt = select(func.count()).select_from(ListItemCompletion).where(
            ListItemCompletion.item_id == item_id
        )
        return int((await self._session.execute(stmt)).scalar_one())
