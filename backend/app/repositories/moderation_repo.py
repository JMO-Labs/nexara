"""
@file moderation_repo.py
@brief Repository for content reports and user blocks.

Provides CRUD operations for the moderation subsystem.  The moderation
UI ships in Phase 2; this repository supports the block-filter pattern
used by all content queries in Phase 1.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.media import Media
from app.models.moderation import ContentReport, UserBlock
from app.models.post import Comment, Post
from app.models.user import User
from app.repositories.base import BaseRepository

_CONTENT_AUTHORS: dict[str, tuple[Any, str]] = {
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


class ModerationRepository(BaseRepository[UserBlock]):
    """
    @brief Async repository for user blocks and content reports.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    moderation-specific query methods.
    """

    model = UserBlock

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_block(
        self,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> UserBlock:
        """
        @brief Create a user block record.

        @param blocker_id UUID of the user initiating the block.
        @param blocked_id UUID of the user being blocked.
        @param community_id Community scope.
        @return The persisted UserBlock instance.
        """
        block = UserBlock(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            community_id=community_id,
        )
        self._session.add(block)
        await self._session.flush()
        await self._session.refresh(block)
        return block

    async def remove_block(
        self,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> None:
        """
        @brief Remove a user block record.

        @param blocker_id UUID of the user who created the block.
        @param blocked_id UUID of the blocked user.
        """
        stmt = (
            delete(UserBlock)
            .where(UserBlock.blocker_id == blocker_id)
            .where(UserBlock.blocked_id == blocked_id)
        )
        await self._session.execute(stmt)

    async def is_blocked(
        self,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> bool:
        """
        @brief Check if a block relationship exists between two users.

        @param blocker_id UUID of the potential blocker.
        @param blocked_id UUID of the potentially blocked user.
        @return True if a block record exists.
        """
        stmt = select(UserBlock).where(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_blocked_user_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        """
        @brief Return the set of user IDs blocked by the given user.

        @param user_id UUID of the user whose block list to retrieve.
        @return Set of blocked user UUIDs.
        """
        stmt = select(UserBlock.blocked_id).where(
            UserBlock.blocker_id == user_id,
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def create_report(
        self,
        *,
        reporter_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        reason: str,
        description: str | None = None,
        community_id: uuid.UUID,
    ) -> ContentReport:
        """
        @brief Create a content report.

        @param reporter_id UUID of the reporting user.
        @param target_type Type of content being reported (post, comment, message, media).
        @param target_id UUID of the reported content.
        @param reason Short reason for the report.
        @param description Optional detailed description.
        @param community_id Community scope.
        @return The persisted ContentReport instance.
        """
        report = ContentReport(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            description=description,
            status="pending",
            community_id=community_id,
        )
        # Savepoint keeps the outer transaction usable if UNIQUE is violated.
        async with self._session.begin_nested():
            self._session.add(report)
            await self._session.flush()
        await self._session.refresh(report)
        return report

    async def get_report(
        self, report_id: uuid.UUID, community_id: uuid.UUID
    ) -> ContentReport | None:
        """
        @brief Fetch a report by id within a community.

        @param report_id Report UUID.
        @param community_id Community scope.
        @return The report or None.
        """
        stmt = select(ContentReport).where(
            ContentReport.id == report_id,
            ContentReport.community_id == community_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_reviewed(
        self,
        report: ContentReport,
        *,
        status: str,
        action_taken: str,
        admin_notes: str | None,
        reviewed_by: uuid.UUID,
    ) -> ContentReport:
        """
        @brief Record an admin decision on a report.

        @param report The report to update.
        @param status New status (reviewed or dismissed).
        @param action_taken Admin action key.
        @param admin_notes Optional admin note.
        @param reviewed_by Admin user UUID.
        @return The updated report.
        """
        report.status = status
        report.action_taken = action_taken
        report.admin_notes = admin_notes
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(report)
        return report

    async def list_blocks(self, blocker_id: uuid.UUID, community_id: uuid.UUID) -> list[UserBlock]:
        """
        @brief List blocks created by a user, newest first.

        @param blocker_id Blocking user UUID.
        @param community_id Community scope.
        @return List of UserBlock rows.
        """
        stmt = (
            select(UserBlock)
            .where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.community_id == community_id,
            )
            .order_by(UserBlock.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

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
        model, column = _CONTENT_AUTHORS[target_type]
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
        model, _col = _CONTENT_AUTHORS[target_type]
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

    async def soft_delete_content(
        self, target_type: str, target_id: uuid.UUID, community_id: uuid.UUID
    ) -> None:
        """
        @brief Remove reported content from view.

        Models with ``deleted_at`` (posts) are soft-deleted; comments, chat
        messages and media have no soft-delete column and are hard-deleted.

        @param target_type post, comment, message or media.
        @param target_id Content UUID.
        @param community_id Community scope.
        """
        model, _col = _CONTENT_AUTHORS[target_type]
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

    async def list_reports(
        self,
        *,
        status_filter: str | None = None,
        community_id: uuid.UUID | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[ContentReport], str | None]:
        """
        @brief List content reports with optional status filter and pagination.

        @param status_filter Filter by report status (pending, reviewed, dismissed).
        @param community_id Scope to a specific community.
        @param limit Max items per page.
        @param cursor Opaque cursor for pagination.
        @return Tuple of (reports, next_cursor).
        """
        stmt = select(ContentReport).order_by(
            ContentReport.created_at.desc(), ContentReport.id.desc()
        )

        if status_filter:
            stmt = stmt.where(ContentReport.status == status_filter)
        if community_id:
            stmt = stmt.where(ContentReport.community_id == community_id)
        position = decode_report_cursor(cursor) if cursor else None
        if position is not None:
            ts, last_id = position
            stmt = stmt.where(
                or_(
                    ContentReport.created_at < ts,
                    and_(ContentReport.created_at == ts, ContentReport.id < last_id),
                )
            )

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = encode_report_cursor(rows[-1].created_at, rows[-1].id)

        return rows, next_cursor

    async def set_nsfw(self, kind: str, entity_id: uuid.UUID, community_id: uuid.UUID) -> bool:
        """
        @brief Flag a post or media item as NSFW within a community.

        Posts must not be soft-deleted. Media has no soft-delete column.

        @param kind "posts" or "media".
        @param entity_id Target UUID.
        @param community_id Community scope.
        @return True if a row was updated, False if missing/out of scope.
        """
        if kind == "posts":
            stmt = (
                update(Post)
                .where(Post.id == entity_id, Post.community_id == community_id)
                .where(Post.deleted_at.is_(None))
                .values(is_nsfw=True)
                .returning(Post.id)
            )
        elif kind == "media":
            stmt = (
                update(Media)
                .where(Media.id == entity_id, Media.community_id == community_id)
                .values(is_nsfw=True)
                .returning(Media.id)
            )
        else:
            raise ValueError(f"unsupported kind: {kind}")
        result = await self._session.execute(stmt, execution_options={"synchronize_session": False})
        await self._session.flush()
        return result.scalar_one_or_none() is not None
