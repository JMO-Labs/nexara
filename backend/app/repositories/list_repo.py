"""
@file list_repo.py
@brief Repository for lists: visibility-scoped keyset listing and counters.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, and_, literal, or_, select, tuple_, update

from app.models.list import List, ListMember
from app.models.moderation import UserBlock
from app.repositories.base import BaseRepository
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt

COUNTER_COLUMNS = ("item_count", "completed_count", "signup_count")


class ListRepository(BaseRepository[List]):
    """@brief Async repo for List CRUD with visibility-aware reads."""

    model = List

    async def list_visible(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID] | None = None,
        member_list_ids: list[uuid.UUID] | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[List], str | None]:
        """
        @brief Keyset-list lists visible to the viewer.

        Visible when: community; private and owned by viewer; subgroup and
        viewer belongs to it; members and viewer is an explicit member (or owner).

        @param community_id Tenant scope.
        @param viewer_id Viewing user.
        @param subgroup_ids Subgroups the viewer belongs to.
        @param member_list_ids Lists where the viewer is an explicit member;
            when None, resolved from ``list_member``.
        @param cursor Opaque keyset cursor.
        @param limit Page size.
        @return (lists, next_cursor).
        """
        if member_list_ids is None:
            res = await self._session.execute(
                select(ListMember.list_id).where(ListMember.user_id == viewer_id)
            )
            member_list_ids = list(res.scalars().all())
        visible = or_(
            List.visibility == "community",
            and_(List.visibility == "private", List.owner_id == viewer_id),
            and_(
                List.visibility == "subgroup",
                List.subgroup_id.in_(subgroup_ids) if subgroup_ids else literal(False),
            ),
            and_(
                List.visibility == "members",
                or_(
                    List.owner_id == viewer_id,
                    List.id.in_(member_list_ids) if member_list_ids else literal(False),
                ),
            ),
        )
        stmt = self._base_query().where(List.community_id == community_id, visible)
        stmt = self._block_filter(stmt, viewer_id)
        decoded = decode_cursor(cursor, parse_dt)
        if decoded is not None:
            stmt = stmt.where(tuple_(List.created_at, List.id) < tuple_(*decoded))
        stmt = stmt.order_by(List.created_at.desc(), List.id.desc())
        rows = list((await self._session.execute(stmt.limit(limit + 1))).scalars().all())
        nxt = None
        if len(rows) > limit:
            rows = rows[:limit]
            nxt = encode_cursor(rows[-1].created_at, rows[-1].id)
        return rows, nxt

    @staticmethod
    def _block_filter(stmt: Select[Any], viewer_id: uuid.UUID) -> Select[Any]:
        """@brief Hide lists owned by users in a block relation with the viewer."""
        by_viewer = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        of_viewer = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        return stmt.where(List.owner_id.notin_(by_viewer), List.owner_id.notin_(of_viewer))

    async def increment_counters(self, list_id: uuid.UUID, delta: dict[str, int]) -> None:
        """
        @brief Atomically add deltas to denormalised counters.

        @param list_id List primary key.
        @param delta Mapping of counter column (item_count, completed_count,
            signup_count) to signed increment.
        @raises ValueError On unknown counter names.
        """
        bad = set(delta) - set(COUNTER_COLUMNS)
        if bad:
            raise ValueError(f"Unknown counters: {sorted(bad)}")
        if not delta:
            return
        values = {k: getattr(List, k) + v for k, v in delta.items()}
        await self._session.execute(update(List).where(List.id == list_id).values(**values))
        await self._session.flush()

    async def is_member(self, list_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief True when ``user_id`` has an explicit membership on the list."""
        stmt = select(ListMember.user_id).where(
            ListMember.list_id == list_id, ListMember.user_id == user_id
        )
        return (await self._session.execute(stmt)).first() is not None
