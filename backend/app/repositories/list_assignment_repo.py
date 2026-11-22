"""
@file list_assignment_repo.py
@brief Repository for list item assignments (one active row per item).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.models.list_assignment import ACTIVE_STATUSES, ListItemAssignment
from app.repositories.base import BaseRepository


class ListAssignmentRepository(BaseRepository[ListItemAssignment]):
    """@brief Async repo for ListItemAssignment rows, always community-scoped."""

    model = ListItemAssignment

    async def get_active(
        self, community_id: uuid.UUID, item_id: uuid.UUID
    ) -> ListItemAssignment | None:
        """@brief The pending/accepted assignment of an item, or None."""
        stmt = select(ListItemAssignment).where(
            ListItemAssignment.community_id == community_id,
            ListItemAssignment.item_id == item_id,
            ListItemAssignment.status.in_(ACTIVE_STATUSES),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def active_for_list(
        self, community_id: uuid.UUID, list_id: uuid.UUID
    ) -> dict[uuid.UUID, ListItemAssignment]:
        """@brief Active assignments of a list keyed by item id."""
        stmt = select(ListItemAssignment).where(
            ListItemAssignment.community_id == community_id,
            ListItemAssignment.list_id == list_id,
            ListItemAssignment.status.in_(ACTIVE_STATUSES),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {r.item_id: r for r in rows}

    async def add(
        self,
        community_id: uuid.UUID,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        assignee_id: uuid.UUID,
        assigned_by: uuid.UUID,
        status: str,
    ) -> ListItemAssignment:
        """@brief Insert an assignment (``accepted`` rows get ``responded_at``)."""
        row = ListItemAssignment(
            community_id=community_id,
            list_id=list_id,
            item_id=item_id,
            assignee_id=assignee_id,
            assigned_by=assigned_by,
            status=status,
            responded_at=datetime.now(UTC) if status == "accepted" else None,
        )
        return await self.create(row)

    async def set_status(self, row: ListItemAssignment, status: str) -> ListItemAssignment:
        """@brief Record the assignee's response."""
        row.status = status
        row.responded_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def remove(self, row: ListItemAssignment) -> None:
        """@brief Delete an assignment row (release / unassign)."""
        await self._session.execute(
            delete(ListItemAssignment).where(ListItemAssignment.id == row.id)
        )
        await self._session.flush()
