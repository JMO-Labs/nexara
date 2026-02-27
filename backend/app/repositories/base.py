"""
@file base.py
@brief Generic async CRUD base repository.

Provides reusable ``create``, ``get_by_id``, ``list``, ``update``, and
``soft_delete`` operations.  Domain-specific repositories inherit from
:class:`BaseRepository` and add custom query methods.

All queries include ``community_id`` scoping and soft-delete filtering
by default.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

import structlog
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

logger = structlog.get_logger(__name__)

ModelT = TypeVar("ModelT", bound=Base)
"""@brief Type variable constrained to SQLAlchemy models inheriting from Base."""


class BaseRepository(Generic[ModelT]):  # noqa: UP046
    """
    @brief Generic async CRUD repository.

    Subclasses specify the ``model`` class attribute and gain standard CRUD
    operations automatically.

    @param session Async SQLAlchemy session (injected per-request).

    Usage::

        class UserRepo(BaseRepository[User]):
            model = User
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select:
        """
        @brief Return the base ``SELECT`` statement for this model.

        Applies soft-delete filtering (``deleted_at IS NULL``) when the
        model has a ``deleted_at`` column.  Subclasses may override to
        add additional default filters (e.g. block list).
        """
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[union-attr]
        return stmt

    async def get_by_id(
        self,
        entity_id: uuid.UUID,
        community_id: uuid.UUID | None = None,
    ) -> ModelT | None:
        """
        @brief Fetch a single entity by primary key.

        @param entity_id UUID primary key.
        @param community_id If provided, adds a community_id scope.
        @return The model instance or None.
        """
        stmt = self._base_query().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        if community_id is not None and hasattr(self.model, "community_id"):
            stmt = stmt.where(self.model.community_id == community_id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        community_id: uuid.UUID | None = None,
        *,
        limit: int = 20,
        cursor: str | None = None,
        order_by: Any | None = None,
    ) -> tuple[list[ModelT], str | None]:
        """
        @brief List entities with cursor-based pagination.

        @param community_id Scope results to this community.
        @param limit Max items to return.
        @param cursor Opaque cursor (UUID of the last seen item).
        @param order_by SQLAlchemy column expression; defaults to ``created_at DESC``.
        @return Tuple of (items, next_cursor).
        """
        stmt = self._base_query()
        if community_id is not None and hasattr(self.model, "community_id"):
            stmt = stmt.where(self.model.community_id == community_id)  # type: ignore[attr-defined]

        if order_by is None and hasattr(self.model, "created_at"):
            order_col = self.model.created_at  # type: ignore[attr-defined]
            stmt = stmt.order_by(order_col.desc())
        elif order_by is not None:
            stmt = stmt.order_by(order_by)

        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(self.model.id < cursor_id)  # type: ignore[attr-defined]
            except ValueError:
                pass

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)  # type: ignore[attr-defined]

        return rows, next_cursor

    async def create(self, entity: ModelT) -> ModelT:
        """
        @brief Persist a new entity.

        @param entity The ORM model instance to insert.
        @return The same instance, now with server-generated fields populated.
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, data: dict[str, Any]) -> ModelT:
        """
        @brief Apply partial updates to an existing entity.

        @param entity The ORM instance to update.
        @param data Dict of attribute names to new values.
        @return The updated entity.
        """
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def soft_delete(self, entity: ModelT) -> ModelT:
        """
        @brief Soft-delete an entity by setting ``deleted_at``.

        Falls back to a hard delete if the model has no ``deleted_at`` column.

        @param entity The ORM instance to soft-delete.
        @return The (soft-)deleted entity.
        """
        if hasattr(entity, "deleted_at"):
            from datetime import UTC, datetime

            entity.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
            await self._session.flush()
            return entity
        await self._session.delete(entity)
        await self._session.flush()
        return entity

    async def count(self, community_id: uuid.UUID | None = None) -> int:
        """
        @brief Count entities matching the base query and optional community scope.

        @param community_id Optional community scope.
        @return Integer count.
        """
        stmt = select(func.count()).select_from(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[union-attr]
        if community_id is not None and hasattr(self.model, "community_id"):
            stmt = stmt.where(self.model.community_id == community_id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def apply_block_filter(
        stmt: Select,
        viewer_id: uuid.UUID,
    ) -> Select:
        """
        @brief Exclude content from users that the viewer has blocked (or who blocked the viewer).

        Joins the ``user_blocks`` table and filters out rows where:
        - The content author blocked the viewer, **or**
        - The viewer blocked the content author.

        The model must have a ``user_id`` (or ``author_id``) column referencing
        the content creator.  Callers pass the already-constructed SELECT
        statement; this method returns a new statement with the exclusion applied.

        @param stmt An existing SQLAlchemy SELECT statement.
        @param viewer_id UUID of the currently authenticated user.
        @return Modified SELECT with block exclusions applied.
        """
        from app.models.moderation import UserBlock

        author_col = None
        for col_name in ("user_id", "author_id", "created_by"):
            target = stmt.columns_clause_froms[0] if stmt.columns_clause_froms else object()
            if hasattr(target, col_name):
                author_col = col_name
                break

        if author_col is None:
            return stmt

        model_table = stmt.froms[0] if stmt.froms else None
        if model_table is None:
            return stmt

        author_column = model_table.c[author_col]

        blocked_by_viewer = (
            select(UserBlock.blocked_id)
            .where(UserBlock.blocker_id == viewer_id)
            .correlate(model_table)
        )
        blocked_viewer = (
            select(UserBlock.blocker_id)
            .where(UserBlock.blocked_id == viewer_id)
            .correlate(model_table)
        )

        stmt = stmt.where(author_column.notin_(blocked_by_viewer))
        stmt = stmt.where(author_column.notin_(blocked_viewer))
        return stmt
