"""
@file audit_repo.py
@brief Repository for the append-only audit log.

Audit entries are never updated or deleted.  This repository provides
``append()`` for writing and ``list()`` for reading with pagination.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """
    @brief Async repository for audit log entries.

    Append-only — no update or delete methods are provided.
    """

    model = AuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def append(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        extra_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """
        @brief Create a new audit log entry.

        @param actor_id UUID of the user performing the action (None for system).
        @param action Machine-readable action key (e.g. "branding.updated").
        @param target_type Type of the affected entity (e.g. "user", "branding").
        @param target_id UUID of the affected entity.
        @param extra_data Additional JSON-serializable context.
        @param ip_address IP address of the request originator.
        @return The persisted AuditLog instance.
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            extra_data=extra_data,
            ip_address=ip_address,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def list_entries(
        self,
        *,
        action_filter: str | None = None,
        actor_filter: uuid.UUID | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[AuditLog], str | None]:
        """
        @brief List audit log entries with optional filters and cursor pagination.

        @param action_filter Filter by action key prefix.
        @param actor_filter Filter by actor UUID.
        @param limit Max items per page.
        @param cursor Opaque pagination cursor.
        @return Tuple of (entries, next_cursor).
        """
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

        if action_filter:
            stmt = stmt.where(AuditLog.action.startswith(action_filter))
        if actor_filter:
            stmt = stmt.where(AuditLog.actor_id == actor_filter)
        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(AuditLog.id < cursor_id)
            except ValueError:
                pass

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)

        return rows, next_cursor
