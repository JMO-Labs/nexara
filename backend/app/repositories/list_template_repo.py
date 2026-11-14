"""
@file list_template_repo.py
@brief Repository for list templates (keyset-paginated, visibility-scoped).
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select, tuple_
from sqlalchemy.orm import selectinload

from app.models.list_template import ListTemplate
from app.models.moderation import UserBlock
from app.repositories.base import BaseRepository
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt


class ListTemplateRepository(BaseRepository[ListTemplate]):
    """@brief Async repo for ListTemplate CRUD."""

    model = ListTemplate

    async def get_by_id(
        self,
        entity_id: uuid.UUID,
        community_id: uuid.UUID | None = None,
    ) -> ListTemplate | None:
        """
        @brief Fetch a template with its fields and items eagerly loaded.

        Async sessions cannot lazy-load relationships, and cloning/updating
        reads both collections.

        @param entity_id Template primary key.
        @param community_id Optional tenant scope.
        @return The template or None.
        """
        stmt = self._base_query().where(ListTemplate.id == entity_id)
        if community_id is not None:
            stmt = stmt.where(ListTemplate.community_id == community_id)
        stmt = stmt.options(selectinload(ListTemplate.fields), selectinload(ListTemplate.items))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_community(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[ListTemplate], str | None]:
        """
        @brief List templates the viewer owns or that are shared/system.

        @param community_id Tenant scope.
        @param viewer_id Viewing user.
        @param cursor Opaque keyset cursor.
        @param limit Page size.
        @return (templates, next_cursor).
        """
        stmt = self._base_query().where(
            ListTemplate.community_id == community_id,
            or_(
                ListTemplate.author_id == viewer_id,
                ListTemplate.is_shared.is_(True),
                ListTemplate.is_system.is_(True),
            ),
        )
        # Custom clause: system/orphaned templates have NULL author_id and
        # NOT IN would evaluate to NULL, hiding them.
        by_viewer = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        of_viewer = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        stmt = stmt.where(
            or_(
                ListTemplate.author_id.is_(None),
                and_(
                    ListTemplate.author_id.notin_(by_viewer),
                    ListTemplate.author_id.notin_(of_viewer),
                ),
            )
        )
        decoded = decode_cursor(cursor, parse_dt)
        if decoded is not None:
            stmt = stmt.where(tuple_(ListTemplate.created_at, ListTemplate.id) < tuple_(decoded[0], decoded[1]))
        stmt = stmt.order_by(ListTemplate.created_at.desc(), ListTemplate.id.desc())
        rows = list((await self._session.execute(stmt.limit(limit + 1))).scalars().all())
        nxt = None
        if len(rows) > limit:
            rows = rows[:limit]
            nxt = encode_cursor(rows[-1].created_at, rows[-1].id)
        return rows, nxt
