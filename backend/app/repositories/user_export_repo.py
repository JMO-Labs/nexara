"""
@file user_export_repo.py
@brief Data access for user data exports.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.user_export import UserExport
from app.repositories.base import BaseRepository


class UserExportRepository(BaseRepository[UserExport]):
    """@brief Repository for :class:`UserExport` rows."""

    model = UserExport

    async def create_export(self, user_id: uuid.UUID, community_id: uuid.UUID) -> UserExport:
        """@brief Insert a pending export. @return The persisted export."""
        return await self.create(
            UserExport(user_id=user_id, community_id=community_id, status="pending")
        )

    async def get_latest_by_user(self, user_id: uuid.UUID) -> UserExport | None:
        """@brief Most recent export for a user, or None."""
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
        """@brief Set status and any provided fields. @raises NotFoundError."""
        export = await self.get_by_id(export_id)
        if export is None:
            raise NotFoundError("Export not found")
        export.status = status
        for name, value in (
            ("file_key", file_key),
            ("file_size_bytes", file_size_bytes),
            ("error_message", error_message),
            ("ready_at", ready_at),
            ("expires_at", expires_at),
        ):
            if value is not None:
                setattr(export, name, value)
        await self._session.flush()
        await self._session.refresh(export)
        return export
