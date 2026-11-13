"""
@file gallery_service.py
@brief Gallery business logic — CRUD and listing; items/admin live in mixins.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.event import Event
from app.models.gallery import Gallery
from app.schemas.gallery import (
    GalleryCreate,
    GalleryList,
    GalleryResponse,
    GalleryUpdate,
)
from app.services.activity_publish import record_activity
from app.services.gallery_admin import GalleryAdminMixin
from app.services.gallery_items import GalleryItemsMixin


class GalleryService(GalleryItemsMixin, GalleryAdminMixin):
    """@brief Service layer for galleries."""

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create_gallery(self, user_id: uuid.UUID, data: GalleryCreate) -> GalleryResponse:
        if data.visibility == "subgroup" and data.subgroup_id is None:
            raise AppError(
                code="SUBGROUP_REQUIRED",
                message=_("Subgroup is required for subgroup-scoped galleries"),
                status_code=400,
            )

        gallery = Gallery(
            community_id=self._community_id,
            owner_id=user_id,
            title=data.title,
            description=data.description,
            visibility=data.visibility,
            contribution_policy=data.contribution_policy,
            subgroup_id=data.subgroup_id,
            event_id=data.event_id,
            cover_media_id=data.cover_media_id,
        )
        gallery = await self._repo.create(gallery)

        if self._activity_repo is not None:
            from app.models.user import User

            user_result = await self._session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            user_name = user.display_name if user else "Unknown"

            await record_activity(
                self._activity_repo,
                self._session,
                None,
                community_id=self._community_id,
                actor_id=user_id,
                verb="gallery.created",
                object_type="gallery",
                object_id=gallery.id,
                subgroup_id=gallery.subgroup_id,
                visibility=gallery.visibility,
                target_type="subgroup" if gallery.subgroup_id else "community",
                target_id=gallery.subgroup_id or self._community_id,
                metadata={
                    "actor_name": user_name,
                    "object_title": gallery.title,
                },
            )

        await invalidate_search_cache_for_community(self._community_id)
        return GalleryResponse.model_validate(gallery)

    async def get_or_create_for_event(
        self, event_id: uuid.UUID, *, viewer_id: uuid.UUID
    ) -> GalleryResponse:
        """@brief Get-or-create gallery for event, tied to event's visibility/subgroup.

        @param event_id UUID of the event.
        @param viewer_id UUID of the requesting user (checked for event visibility).
        @return GalleryResponse.
        @raises NotFoundError If the event is not found or not visible to viewer.
        """
        # Check for existing gallery first
        existing = await self._repo.get_event_gallery(self._community_id, event_id)
        if existing is not None:
            return GalleryResponse.model_validate(existing)

        # Fetch the event to verify visibility and extract properties
        event = await self._session.get(Event, event_id)
        if event is None:
            raise NotFoundError(_("Event not found"))

        # Check visibility (using same logic as event service)
        if not await self._can_view_event(event, viewer_id):
            raise AuthorizationError(_("You cannot view this event"))

        # Create gallery with event's properties
        gallery = Gallery(
            community_id=self._community_id,
            owner_id=event.author_id,
            title=event.title,
            visibility=event.visibility,
            contribution_policy="community",
            subgroup_id=event.subgroup_id,
            event_id=event.id,
        )
        gallery = await self._repo.create(gallery)
        return GalleryResponse.model_validate(gallery)

    async def _can_view_event(self, event: Event, user_id: uuid.UUID) -> bool:
        """@brief Check if user can view an event (same visibility logic as EventService)."""
        if event.visibility == "community":
            return True
        if event.visibility == "private":
            return event.author_id == user_id
        if event.visibility == "subgroup":
            if event.subgroup_id is None:
                return False
            ids = await self._user_subgroup_ids(user_id)
            return event.subgroup_id in ids
        return False

    async def get_gallery(self, gallery_id: uuid.UUID, user_id: uuid.UUID) -> GalleryResponse:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if not await self._can_view(gallery, user_id):
            raise AuthorizationError(_("You cannot view this gallery"))
        return GalleryResponse.model_validate(gallery)

    async def update_gallery(
        self, gallery_id: uuid.UUID, user_id: uuid.UUID, data: GalleryUpdate
    ) -> GalleryResponse:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if gallery.owner_id != user_id:
            raise AuthorizationError(_("Only the gallery owner can edit this gallery"))

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(UTC)
        gallery = await self._repo.update(gallery, update_data)
        await invalidate_search_cache_for_community(self._community_id)
        return GalleryResponse.model_validate(gallery)

    async def delete_gallery(self, gallery_id: uuid.UUID, user_id: uuid.UUID) -> None:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if gallery.owner_id != user_id:
            raise AuthorizationError(_("Only the gallery owner can delete this gallery"))
        await self._session.delete(gallery)
        await self._session.flush()
        if self._activity_repo is not None:
            await self._activity_repo.invalidate("gallery", gallery_id)

    async def search(
        self,
        *,
        q: str,
        viewer_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> GalleryList:
        """@brief Search galleries by title and description, respecting visibility."""
        rows = await self._repo.search(
            q=q,
            viewer_id=viewer_id,
            community_id=self._community_id,
            limit=limit,
            offset=offset,
        )
        # Filter by visibility for each result
        visible_rows = []
        for gallery in rows:
            if await self._can_view(gallery, viewer_id):
                visible_rows.append(gallery)
        return GalleryList(
            items=[GalleryResponse.model_validate(r) for r in visible_rows],
            next_cursor=None,
            has_more=False,
        )

    async def list_galleries(
        self,
        user_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
        subgroup_id: uuid.UUID | None = None,
        featured_only: bool = False,
        sort: str = "recent",
        cursor: str | None = None,
        limit: int = 20,
    ) -> GalleryList:
        subgroup_ids = await self._user_subgroup_ids(user_id)
        rows, next_cursor = await self._repo.list_visible(
            self._community_id,
            viewer_id=user_id,
            subgroup_ids=subgroup_ids,
            owner_id=owner_id,
            event_id=event_id,
            subgroup_id=subgroup_id,
            featured_only=featured_only,
            sort=sort,
            limit=limit,
            cursor=cursor,
        )
        return GalleryList(
            items=[GalleryResponse.model_validate(r) for r in rows],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
