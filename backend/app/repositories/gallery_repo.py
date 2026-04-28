"""
@file gallery_repo.py
@brief Repository for galleries, gallery items, and collaborators.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, delete, func, literal, or_, select, update

from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.repositories.base import BaseRepository

__all__ = ["GalleryRepository"]


class GalleryRepository(BaseRepository[Gallery]):
    """@brief Async repo for gallery CRUD + items + collaborators."""

    model = Gallery

    async def search(
        self,
        *,
        q: str,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Gallery]:
        """@brief Full-text search on galleries using search_fts column."""
        ts_query = func.plainto_tsquery("simple", q)
        stmt = (
            select(Gallery)
            .where(
                Gallery.community_id == community_id,
                Gallery.search_fts.op("@@")(ts_query),
            )
            .order_by(func.ts_rank(Gallery.search_fts, ts_query).desc())
            .limit(limit)
            .offset(offset)
        )
        stmt = self.apply_block_filter(stmt, viewer_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_visible(
        self,
        community_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID,
        subgroup_ids: list[uuid.UUID] | None = None,
        owner_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
        subgroup_id: uuid.UUID | None = None,
        featured_only: bool = False,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[Gallery], str | None]:
        """@brief List galleries visible to a viewer with optional filters."""
        stmt = select(Gallery).where(Gallery.community_id == community_id)

        allowed = subgroup_ids or []
        visible = or_(
            Gallery.visibility == "community",
            and_(Gallery.visibility == "private", Gallery.owner_id == viewer_id),
            and_(
                Gallery.visibility == "subgroup",
                Gallery.subgroup_id.in_(allowed) if allowed else literal(False),
            ),
        )
        stmt = stmt.where(visible)

        if owner_id is not None:
            stmt = stmt.where(Gallery.owner_id == owner_id)
        if event_id is not None:
            stmt = stmt.where(Gallery.event_id == event_id)
        if subgroup_id is not None:
            stmt = stmt.where(Gallery.subgroup_id == subgroup_id)
        if featured_only:
            stmt = stmt.where(Gallery.is_featured.is_(True))

        stmt = self.apply_block_filter(stmt, viewer_id)
        stmt = stmt.order_by(Gallery.updated_at.desc()).limit(limit + 1)

        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(Gallery.id < cursor_id)
            except ValueError:
                pass

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)
        return rows, next_cursor

    async def get_default_for_user(
        self, community_id: uuid.UUID, user_id: uuid.UUID
    ) -> Gallery | None:
        """@brief Fetch the default gallery for a user (one per user)."""
        stmt = select(Gallery).where(
            Gallery.community_id == community_id,
            Gallery.owner_id == user_id,
            Gallery.is_default.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_event_gallery(
        self, community_id: uuid.UUID, event_id: uuid.UUID
    ) -> Gallery | None:
        """@brief Fetch the auto-created gallery for an event."""
        stmt = select(Gallery).where(
            Gallery.community_id == community_id,
            Gallery.event_id == event_id,
            Gallery.is_event_gallery.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Items ─────────────────────────────────────────────────────────

    async def list_items(
        self, gallery_id: uuid.UUID, *, limit: int = 100, cursor: str | None = None
    ) -> tuple[list[GalleryItem], str | None]:
        """@brief List items in a gallery ordered by position."""
        stmt = (
            select(GalleryItem)
            .where(GalleryItem.gallery_id == gallery_id)
            .order_by(GalleryItem.position.asc(), GalleryItem.created_at.asc())
            .limit(limit + 1)
        )
        if cursor:
            try:
                stmt = stmt.where(GalleryItem.id > uuid.UUID(cursor))
            except ValueError:
                pass

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)
        return rows, next_cursor

    async def get_item(self, gallery_id: uuid.UUID, media_id: uuid.UUID) -> GalleryItem | None:
        """@brief Fetch a single item by gallery + media."""
        stmt = select(GalleryItem).where(
            GalleryItem.gallery_id == gallery_id,
            GalleryItem.media_id == media_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_item(self, item: GalleryItem) -> GalleryItem:
        """@brief Insert a gallery item and bump gallery item_count."""
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        await self._session.execute(
            update(Gallery)
            .where(Gallery.id == item.gallery_id)
            .values(item_count=Gallery.item_count + 1)
        )
        await self._session.flush()
        return item

    async def update_item(self, item: GalleryItem, data: dict[str, Any]) -> GalleryItem:
        """@brief Update mutable fields on an item."""
        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def remove_item(self, item: GalleryItem) -> None:
        """@brief Delete a gallery item and decrement gallery item_count."""
        gallery_id = item.gallery_id
        await self._session.delete(item)
        await self._session.execute(
            update(Gallery)
            .where(Gallery.id == gallery_id, Gallery.item_count > 0)
            .values(item_count=Gallery.item_count - 1)
        )
        await self._session.flush()

    async def count_items(self, gallery_id: uuid.UUID) -> int:
        """@brief Return current item count for a gallery."""
        stmt = (
            select(func.count())
            .select_from(GalleryItem)
            .where(GalleryItem.gallery_id == gallery_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    # ── Collaborators ─────────────────────────────────────────────────

    async def list_collaborators(self, gallery_id: uuid.UUID) -> list[GalleryCollaborator]:
        """@brief List collaborators for a gallery."""
        stmt = select(GalleryCollaborator).where(GalleryCollaborator.gallery_id == gallery_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_collaborator(
        self,
        gallery_id: uuid.UUID,
        user_id: uuid.UUID,
        invited_by: uuid.UUID | None,
    ) -> GalleryCollaborator:
        """@brief Add a collaborator to a gallery."""
        collab = GalleryCollaborator(gallery_id=gallery_id, user_id=user_id, invited_by=invited_by)
        self._session.add(collab)
        await self._session.flush()
        return collab

    async def is_collaborator(self, gallery_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Check if a user is a collaborator on a gallery."""
        stmt = select(GalleryCollaborator).where(
            GalleryCollaborator.gallery_id == gallery_id,
            GalleryCollaborator.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def remove_collaborator(self, gallery_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """@brief Remove a collaborator from a gallery."""
        stmt = delete(GalleryCollaborator).where(
            GalleryCollaborator.gallery_id == gallery_id,
            GalleryCollaborator.user_id == user_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()
