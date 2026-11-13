"""
@file moderation_repo.py
@brief Repository for content reports and user blocks.

Provides CRUD operations for the moderation subsystem.  The moderation
UI ships in Phase 2; this repository supports the block-filter pattern
used by all content queries in Phase 1.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.moderation import ContentReport, UserBlock
from app.models.post import Post
from app.models.user import User
from app.repositories.base import BaseRepository


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

    async def is_blocked_either(self, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
        """
        @brief Check whether either user has blocked the other.

        @param user_a First user UUID.
        @param user_b Second user UUID.
        @return True if a block exists in either direction.
        """
        stmt = select(UserBlock.id).where(
            or_(
                and_(UserBlock.blocker_id == user_a, UserBlock.blocked_id == user_b),
                and_(UserBlock.blocker_id == user_b, UserBlock.blocked_id == user_a),
            )
        )
        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def list_blocked_users(self, user_id: uuid.UUID, community_id: uuid.UUID) -> list[User]:
        """
        @brief Return users the given user has blocked, newest block first.

        @param user_id Blocker UUID.
        @param community_id Community scope.
        @return List of blocked User rows.
        """
        stmt = (
            select(User)
            .join(UserBlock, UserBlock.blocked_id == User.id)
            .where(UserBlock.blocker_id == user_id, UserBlock.community_id == community_id)
            .order_by(UserBlock.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

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
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)
        return report

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
        stmt = select(ContentReport).order_by(ContentReport.created_at.desc())

        if status_filter:
            stmt = stmt.where(ContentReport.status == status_filter)
        if community_id:
            stmt = stmt.where(ContentReport.community_id == community_id)
        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(ContentReport.id < cursor_id)
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
