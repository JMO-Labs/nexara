"""
@file user_export_repo.py
@brief Data access for user data-export requests.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.models.user_export import UserExport
from app.repositories.base import BaseRepository


class UserExportRepository(BaseRepository[UserExport]):
    """@brief Repository for :class:`UserExport` rows."""

    model = UserExport

    async def create(self, user_id: uuid.UUID, community_id: uuid.UUID) -> UserExport:
        """@brief Insert a pending export. @return The persisted row."""
        row = UserExport(user_id=user_id, community_id=community_id, status="pending")
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, export_id: uuid.UUID) -> UserExport | None:
        """@brief Fetch an export by id. @return Row or None."""
        stmt = select(UserExport).where(UserExport.id == export_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_latest_by_user(self, user_id: uuid.UUID) -> UserExport | None:
        """@brief Most recent export for a user. @return Row or None."""
        stmt = (
            select(UserExport)
            .where(UserExport.user_id == user_id)
            .order_by(UserExport.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update_status(
        self,
        export_id: uuid.UUID,
        status: str,
        *,
        file_key: str | None = None,
        file_size_bytes: int | None = None,
        error_message: str | None = None,
        ready_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> UserExport:
        """
        @brief Update status and any provided lifecycle fields.
        @raises LookupError If the export does not exist.
        """
        row = await self.get_by_id(export_id)
        if row is None:
            raise LookupError(f"export {export_id} not found")
        row.status = status
        for name, value in (
            ("file_key", file_key),
            ("file_size_bytes", file_size_bytes),
            ("error_message", error_message),
            ("ready_at", ready_at),
            ("expires_at", expires_at),
        ):
            if value is not None:
                setattr(row, name, value)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def commit(self) -> None:
        """@brief Commit so a queued worker can see the row."""
        await self._session.commit()
