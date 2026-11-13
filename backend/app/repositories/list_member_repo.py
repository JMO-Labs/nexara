"""
@file list_member_repo.py
@brief Repository for explicit list membership.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models.list import ListMember
from app.repositories.base import BaseRepository


class ListMemberRepository(BaseRepository[ListMember]):
    """@brief Async repo for ListMember rows (composite PK list_id, user_id).

    @note No ``id`` column: inherited ``get_by_id`` is unusable; use ``get_member``.
    """

    model = ListMember

    async def get_member(self, list_id: uuid.UUID, user_id: uuid.UUID) -> ListMember | None:
        """@brief Fetch one membership."""
        stmt = self._base_query().where(
            ListMember.list_id == list_id, ListMember.user_id == user_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_members(self, list_id: uuid.UUID) -> list[ListMember]:
        """@brief All members of a list, oldest first."""
        stmt = (
            self._base_query()
            .where(ListMember.list_id == list_id)
            .order_by(ListMember.added_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_member(
        self, list_id: uuid.UUID, user_id: uuid.UUID, role: str = "viewer"
    ) -> ListMember:
        """@brief Add a member with a role."""
        return await self.create(ListMember(list_id=list_id, user_id=user_id, role=role))

    async def update_member(self, member: ListMember, data: dict[str, Any]) -> ListMember:
        """@brief Update role / share_personal on a membership."""
        return await self.update(member, data)

    async def remove_member(self, member: ListMember) -> None:
        """@brief Hard-delete a membership (no soft-delete column)."""
        await self.soft_delete(member)
