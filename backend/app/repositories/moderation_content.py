"""
@file moderation_content.py
@brief Report cursor helpers and reported-content lookups for moderation.

Split out of ``moderation_repo.py`` to keep modules under 400 lines.
:class:`ModerationContentMixin` is mixed into ``ModerationRepository``.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.media import Media
from app.models.post import Comment, Post
from app.models.user import User

CONTENT_AUTHORS: dict[str, tuple[Any, str]] = {
    "post": (Post, "author_id"),
    "comment": (Comment, "author_id"),
    "message": (ChatMessage, "author_id"),
    "media": (Media, "uploader_id"),
}
"""@brief Map of report target_type to (model, author column)."""


def encode_report_cursor(created_at: datetime, report_id: uuid.UUID) -> str:
    """
    @brief Encode a ``(created_at, id)`` keyset position as an opaque cursor.

    @param created_at Timestamp of the last returned report.
    @param report_id UUID of the last returned report.
    @return URL-safe base64 string.
    """
    raw = f"{created_at.isoformat()},{report_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_report_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    """
    @brief Decode a cursor produced by :func:`encode_report_cursor`.

    @param cursor Opaque cursor string.
    @return ``(created_at, id)`` or None when unparseable.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode()
        ts_str, id_str = raw.split(",", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except (ValueError, UnicodeDecodeError, TypeError):
        return None


class ModerationContentMixin:
    """@brief Lookups and actions on reported content and its authors."""

    _session: AsyncSession

    async def get_content_author_id(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> uuid.UUID | None:
        """
        @brief Resolve the author/owner of reported content in a community.

        @param target_type post, comment, message or media.
        @param target_id Content UUID.
        @param community_id Community scope.
        @return Author UUID or None if unknown.
        """
        model, column = CONTENT_AUTHORS[target_type]
        stmt = select(getattr(model, column)).where(
            model.id == target_id, model.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def content_exists(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """
        @brief Check that reportable content exists in the community.

        @param target_type post, comment, message or media.
        @param target_id Content UUID.
        @param community_id Community scope.
        @return True if the row exists (and is not soft-deleted).
        """
        model, _col = CONTENT_AUTHORS[target_type]
        stmt = select(model.id).where(model.id == target_id, model.community_id == community_id)
        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def user_exists(self, user_id: uuid.UUID, community_id: uuid.UUID) -> bool:
        """
        @brief Check that a non-deleted user exists in the community.

        @param user_id User UUID.
        @param community_id Community scope.
        @return True if the user exists.
        """
        stmt = select(User.id).where(
            User.id == user_id,
            User.community_id == community_id,
            User.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def get_user_role(self, user_id: uuid.UUID, community_id: uuid.UUID) -> str | None:
        """
        @brief Fetch a user's role within a community.

        @param user_id User UUID.
        @param community_id Community scope.
        @return Role string or None if the user is unknown.
        """
        stmt = select(User.role).where(User.id == user_id, User.community_id == community_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def hide_content(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """
        @brief Reversibly hide reported content (sets ``deleted_at``).

        Only models with a ``deleted_at`` column (posts) can be hidden.
        Other targets are left untouched; never issues a DELETE.

        @param target_type post, comment, message or media.
        @param target_id Content UUID.
        @param community_id Community scope.
        @return True if hidden, False if the target type cannot be hidden.
        """
        model, _col = CONTENT_AUTHORS[target_type]
        if not hasattr(model, "deleted_at"):
            return False
        await self._session.execute(
            update(model)
            .where(model.id == target_id, model.community_id == community_id)
            .values(deleted_at=datetime.now(UTC))
        )
        return True

    async def soft_delete_content(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> None:
        """
        @brief Remove reported content (``delete_content`` action).

        Models with ``deleted_at`` (posts) are soft-deleted; comments, chat
        messages and media have no soft-delete column and are hard-deleted.

        @param target_type post, comment, message or media.
        @param target_id Content UUID.
        @param community_id Community scope.
        """
        model, _col = CONTENT_AUTHORS[target_type]
        scope = (model.id == target_id, model.community_id == community_id)
        if hasattr(model, "deleted_at"):
            await self._session.execute(
                update(model).where(*scope).values(deleted_at=datetime.now(UTC))
            )
        else:
            await self._session.execute(delete(model).where(*scope))

    async def deactivate_user(self, user_id: uuid.UUID, community_id: uuid.UUID) -> None:
        """
        @brief Deactivate (ban) a user account within a community.

        @param user_id User UUID.
        @param community_id Community scope.
        """
        await self._session.execute(
            update(User)
            .where(User.id == user_id, User.community_id == community_id)
            .values(is_active=False)
        )
