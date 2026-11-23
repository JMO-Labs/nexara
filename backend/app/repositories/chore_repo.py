"""
@file chore_repo.py
@brief Queries for repeating list chores: due scan, eligibility, recap.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import List, ListItem, ListItemCompletion
from app.models.list_assignment import ACTIVE_STATUSES, ListItemAssignment
from app.models.moderation import UserBlock
from app.models.user import User


class ChoreRepository:
    """@brief Async queries behind :class:`ChoreService`."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Async SQLAlchemy session."""
        self._session = session

    async def due_item_ids(self, now: datetime, limit: int = 200) -> list[uuid.UUID]:
        """@return Ids of live repeating items whose ``next_due_at`` has passed."""
        stmt = (
            select(ListItem.id)
            .join(List, List.id == ListItem.list_id)
            .where(
                List.deleted_at.is_(None),
                ListItem.repeat.is_not(None),
                ListItem.deleted_at.is_(None),
                ListItem.next_due_at <= now,
            )
            .order_by(ListItem.next_due_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def lock_due(self, item_id: uuid.UUID, now: datetime) -> ListItem | None:
        """
        @brief Lock one item row if it is still due (``FOR UPDATE SKIP LOCKED``).
        @return The locked item, or None when another worker has it or it moved on.
        """
        stmt = (
            select(ListItem)
            .join(List, List.id == ListItem.list_id)
            .where(
                List.deleted_at.is_(None),
                ListItem.id == item_id,
                ListItem.repeat.is_not(None),
                ListItem.deleted_at.is_(None),
                ListItem.next_due_at <= now,
            )
            .with_for_update(of=ListItem, skip_locked=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def usable_users(
        self, ids: set[uuid.UUID], owner_id: uuid.UUID, community_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """
        @brief Subset of ``ids`` that may be rotated in or notified.

        Excludes users of other communities, deactivated, deleted and memorialized
        users and anyone in a block relation (either direction) with the list owner.
        """
        if not ids:
            return set()
        stmt = select(User.id).where(
            User.id.in_(ids),
            User.community_id == community_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.memorialized_at.is_(None),
        )
        ok = set((await self._session.execute(stmt)).scalars().all())
        blocks = select(UserBlock.blocker_id, UserBlock.blocked_id).where(
            or_(
                (UserBlock.blocker_id == owner_id) & UserBlock.blocked_id.in_(ids),
                (UserBlock.blocked_id == owner_id) & UserBlock.blocker_id.in_(ids),
            )
        )
        for blocker, blocked in (await self._session.execute(blocks)).all():
            ok.discard(blocked if blocker == owner_id else blocker)
        return ok

    async def clear_completions(self, item_id: uuid.UUID) -> None:
        """@brief Delete every per-user completion row of an item."""
        await self._session.execute(
            delete(ListItemCompletion).where(ListItemCompletion.item_id == item_id)
        )

    async def assigned_chores(
        self, community_id: uuid.UUID, user_id: uuid.UUID, until: datetime
    ) -> list[tuple[ListItem, List]]:
        """@return Open repeating items actively assigned to the user, due by ``until``."""
        stmt = (
            select(ListItem, List)
            .join(ListItemAssignment, ListItemAssignment.item_id == ListItem.id)
            .join(List, List.id == ListItem.list_id)
            .where(
                ListItemAssignment.community_id == community_id,
                ListItemAssignment.assignee_id == user_id,
                ListItemAssignment.status.in_(ACTIVE_STATUSES),
                ListItem.repeat.is_not(None),
                ListItem.completed.is_(False),
                ListItem.deleted_at.is_(None),
                List.deleted_at.is_(None),
                ListItem.next_due_at <= until,
            )
            .order_by(ListItem.next_due_at)
        )
        return [(i, lst) for i, lst in (await self._session.execute(stmt)).all()]
