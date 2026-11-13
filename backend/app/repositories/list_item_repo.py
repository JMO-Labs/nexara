"""
@file list_item_repo.py
@brief Repository for list items with keyset pagination and row locking.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import ListItem, ListItemCompletion
from app.repositories.base import BaseRepository
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt

_SORTS: dict[str, tuple[Any, Any]] = {
    "position": (ListItem.position, int),
    "created_at": (ListItem.created_at, parse_dt),
}


class ListItemRepository(BaseRepository[ListItem]):
    """@brief Async repo for ListItem CRUD."""

    model = ListItem

    async def list_items_keyset(
        self,
        list_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "position",
    ) -> tuple[list[ListItem], str | None]:
        """
        @brief Page through a list's items in ascending ``sort_by`` order.

        @param list_id Parent list.
        @param cursor Opaque keyset cursor.
        @param limit Page size.
        @param sort_by ``position`` or ``created_at``.
        @return (items, next_cursor).
        @raises ValueError On unsupported ``sort_by``.
        """
        if sort_by not in _SORTS:
            raise ValueError(f"Unsupported sort_by: {sort_by}")
        col, cast = _SORTS[sort_by]
        stmt = self._base_query().where(ListItem.list_id == list_id)
        decoded = decode_cursor(cursor, cast)
        if decoded is not None:
            stmt = stmt.where(tuple_(col, ListItem.id) > tuple_(*decoded))
        stmt = stmt.order_by(col.asc(), ListItem.id.asc())
        rows = list((await self._session.execute(stmt.limit(limit + 1))).scalars().all())
        nxt = None
        if len(rows) > limit:
            rows = rows[:limit]
            nxt = encode_cursor(getattr(rows[-1], sort_by), rows[-1].id)
        return rows, nxt

    async def lock_item_for_update(
        self, item_id: uuid.UUID, session: AsyncSession | None = None
    ) -> ListItem | None:
        """
        @brief Fetch an item with ``SELECT ... FOR UPDATE`` to serialise claims.

        @param item_id Item primary key.
        @param session Session holding the transaction; defaults to the repo's.
        @return Locked item or None.
        """
        stmt = self._base_query().where(ListItem.id == item_id).with_for_update()
        result = await (session or self._session).execute(stmt)
        return result.scalar_one_or_none()

    async def count_live_and_completed(self, list_id: uuid.UUID) -> tuple[int, int]:
        """
        @brief Count live items and completed items (global or per-user completions).

        @param list_id Parent list.
        @return (item_count, completed_count).
        """
        live = (ListItem.list_id == list_id, ListItem.deleted_at.is_(None))
        done = func.count(ListItem.id).filter(ListItem.completed.is_(True))
        per_user = (
            select(func.count(func.distinct(ListItemCompletion.item_id)))
            .join(ListItem, ListItem.id == ListItemCompletion.item_id)
            .where(*live, ListItem.completed.is_(False))
            .scalar_subquery()
        )
        stmt = select(func.count(ListItem.id), done + per_user).where(*live)
        total, completed = (await self._session.execute(stmt)).one()
        return int(total), int(completed)
