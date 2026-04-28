"""
@file gallery_service.py
@brief Gallery business logic — CRUD, items, collaborators, auto-population.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.models.subgroup import SubgroupMember
from app.repositories.gallery_repo import GalleryRepository
from app.schemas.gallery import (
    CollaboratorResponse,
    GalleryCreate,
    GalleryItemBulkCreate,
    GalleryItemCreate,
    GalleryItemResponse,
    GalleryItemUpdate,
    GalleryList,
    GalleryResponse,
    GalleryUpdate,
)

logger = structlog.get_logger(__name__)


class GalleryService:
    """@brief Service layer for galleries."""

    def __init__(
        self,
        gallery_repo: GalleryRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        *,
        notification_service: Any | None = None,
    ) -> None:
        self._repo = gallery_repo
        self._community_id = community_id
        self._session = session
        self._notifications = notification_service

    # ── Helpers ───────────────────────────────────────────────────────

    async def _user_subgroup_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Direct memberships expanded with descendants (parent → child cascade)."""
        from app.repositories.subgroup_repo import expand_with_descendants

        stmt = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == user_id)
        result = await self._session.execute(stmt)
        direct = list(result.scalars().all())
        return await expand_with_descendants(self._session, direct)

    async def _can_view(self, gallery: Gallery, user_id: uuid.UUID) -> bool:
        if gallery.visibility == "community":
            return True
        if gallery.visibility == "private":
            if gallery.owner_id == user_id:
                return True
            return await self._repo.is_collaborator(gallery.id, user_id)
        if gallery.visibility == "subgroup":
            if gallery.subgroup_id is None:
                return False
            ids = await self._user_subgroup_ids(user_id)
            return gallery.subgroup_id in ids
        return False

    async def _can_contribute(self, gallery: Gallery, user_id: uuid.UUID) -> bool:
        if gallery.owner_id == user_id:
            return True
        policy = gallery.contribution_policy
        if policy == "owner_only":
            return False
        if policy == "collaborators":
            return await self._repo.is_collaborator(gallery.id, user_id)
        if policy == "community":
            return await self._can_view(gallery, user_id)
        return False

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
        return GalleryResponse.model_validate(gallery)

    async def ensure_default_gallery(self, user_id: uuid.UUID) -> GalleryResponse:
        """@brief Get-or-create the default "All Photos" gallery for a user."""
        existing = await self._repo.get_default_for_user(self._community_id, user_id)
        if existing is not None:
            return GalleryResponse.model_validate(existing)

        gallery = Gallery(
            community_id=self._community_id,
            owner_id=user_id,
            title="All Photos",
            description=None,
            visibility="private",
            contribution_policy="owner_only",
            is_default=True,
        )
        gallery = await self._repo.create(gallery)
        return GalleryResponse.model_validate(gallery)

    async def ensure_event_gallery(
        self, event_id: uuid.UUID, owner_id: uuid.UUID, title: str
    ) -> GalleryResponse:
        """@brief Get-or-create the auto gallery for an event."""
        existing = await self._repo.get_event_gallery(self._community_id, event_id)
        if existing is not None:
            return GalleryResponse.model_validate(existing)

        gallery = Gallery(
            community_id=self._community_id,
            owner_id=owner_id,
            title=title,
            visibility="community",
            contribution_policy="community",
            event_id=event_id,
            is_event_gallery=True,
        )
        gallery = await self._repo.create(gallery)
        return GalleryResponse.model_validate(gallery)

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
        return GalleryResponse.model_validate(gallery)

    async def delete_gallery(self, gallery_id: uuid.UUID, user_id: uuid.UUID) -> None:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if gallery.owner_id != user_id:
            raise AuthorizationError(_("Only the gallery owner can delete this gallery"))
        await self._session.delete(gallery)
        await self._session.flush()

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

    # ── Items ─────────────────────────────────────────────────────────

    async def list_items(
        self,
        gallery_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> list[GalleryItemResponse]:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if not await self._can_view(gallery, user_id):
            raise AuthorizationError(_("You cannot view this gallery"))
        rows, _next = await self._repo.list_items(gallery_id, limit=limit, cursor=cursor)
        return [GalleryItemResponse.model_validate(r) for r in rows]

    async def add_item(
        self, gallery_id: uuid.UUID, user_id: uuid.UUID, data: GalleryItemCreate
    ) -> GalleryItemResponse:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if not await self._can_contribute(gallery, user_id):
            raise AuthorizationError(_("You cannot add items to this gallery"))
        existing = await self._repo.get_item(gallery_id, data.media_id)
        if existing is not None:
            return GalleryItemResponse.model_validate(existing)

        item = GalleryItem(
            community_id=self._community_id,
            gallery_id=gallery_id,
            media_id=data.media_id,
            added_by=user_id,
            caption=data.caption,
            position=data.position if data.position is not None else gallery.item_count,
        )
        item = await self._repo.add_item(item)
        return GalleryItemResponse.model_validate(item)

    async def bulk_add_items(
        self,
        gallery_id: uuid.UUID,
        user_id: uuid.UUID,
        data: GalleryItemBulkCreate,
    ) -> list[GalleryItemResponse]:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if not await self._can_contribute(gallery, user_id):
            raise AuthorizationError(_("You cannot add items to this gallery"))

        position = gallery.item_count
        out: list[GalleryItemResponse] = []
        for media_id in data.media_ids:
            existing = await self._repo.get_item(gallery_id, media_id)
            if existing is not None:
                out.append(GalleryItemResponse.model_validate(existing))
                continue
            item = GalleryItem(
                community_id=self._community_id,
                gallery_id=gallery_id,
                media_id=media_id,
                added_by=user_id,
                position=position,
            )
            item = await self._repo.add_item(item)
            position += 1
            out.append(GalleryItemResponse.model_validate(item))
        return out

    async def update_item(
        self,
        gallery_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: GalleryItemUpdate,
    ) -> GalleryItemResponse:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        item = await self._session.get(GalleryItem, item_id)
        if item is None or item.gallery_id != gallery_id:
            raise NotFoundError(_("Gallery item not found"))
        if gallery.owner_id != user_id and item.added_by != user_id:
            raise AuthorizationError(_("You cannot edit this item"))
        item = await self._repo.update_item(item, data.model_dump(exclude_unset=True))
        return GalleryItemResponse.model_validate(item)

    async def remove_item(
        self,
        gallery_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        item = await self._session.get(GalleryItem, item_id)
        if item is None or item.gallery_id != gallery_id:
            raise NotFoundError(_("Gallery item not found"))
        if gallery.owner_id != user_id and item.added_by != user_id:
            raise AuthorizationError(_("You cannot remove this item"))
        await self._repo.remove_item(item)

    # ── Collaborators ─────────────────────────────────────────────────

    async def list_collaborators(
        self, gallery_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[CollaboratorResponse]:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if not await self._can_view(gallery, user_id):
            raise AuthorizationError(_("You cannot view this gallery"))
        rows = await self._repo.list_collaborators(gallery_id)
        return [CollaboratorResponse.model_validate(r) for r in rows]

    async def add_collaborator(
        self,
        gallery_id: uuid.UUID,
        user_id: uuid.UUID,
        invitee_id: uuid.UUID,
    ) -> CollaboratorResponse:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if gallery.owner_id != user_id:
            raise AuthorizationError(_("Only the gallery owner can invite collaborators"))
        if await self._repo.is_collaborator(gallery_id, invitee_id):
            existing = next(
                (
                    c
                    for c in await self._repo.list_collaborators(gallery_id)
                    if c.user_id == invitee_id
                ),
                None,
            )
            if existing:
                return CollaboratorResponse.model_validate(existing)
        collab: GalleryCollaborator = await self._repo.add_collaborator(
            gallery_id, invitee_id, invited_by=user_id
        )

        if self._notifications:
            try:
                await self._notifications.notify(
                    user_id=invitee_id,
                    type="gallery_activity",
                    payload={
                        "gallery_id": str(gallery_id),
                        "message": _("You were invited to a gallery"),
                        "link": f"/app/galleries/{gallery_id}",
                    },
                    actor_id=user_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("collab_notify_failed", error=str(exc))
        return CollaboratorResponse.model_validate(collab)

    async def remove_collaborator(
        self,
        gallery_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        if gallery.owner_id != user_id and target_user_id != user_id:
            raise AuthorizationError(_("Only the owner or collaborator may remove access"))
        await self._repo.remove_collaborator(gallery_id, target_user_id)

    # ── Auto-population hook ──────────────────────────────────────────

    async def auto_add_to_event_gallery(
        self,
        post_id: uuid.UUID,
        event_id: uuid.UUID,
        media_ids: list[uuid.UUID],
    ) -> list[GalleryItemResponse] | None:
        """@brief Auto-add media from a post to its event's gallery.

        Called after post creation if event_id and media_ids are present.
        Returns list of added items, or None if no media to add.
        """
        if not media_ids:
            return None
        gallery = await self._repo.get_event_gallery(self._community_id, event_id)
        if gallery is None:
            return None
        position = gallery.item_count
        out: list[GalleryItemResponse] = []
        for media_id in media_ids:
            existing = await self._repo.get_item(gallery.id, media_id)
            if existing is not None:
                out.append(GalleryItemResponse.model_validate(existing))
                continue
            item = GalleryItem(
                community_id=self._community_id,
                gallery_id=gallery.id,
                media_id=media_id,
                added_by=gallery.owner_id,
                position=position,
            )
            item = await self._repo.add_item(item)
            position += 1
            out.append(GalleryItemResponse.model_validate(item))
        return out

    async def auto_add_to_default(
        self, user_id: uuid.UUID, media_id: uuid.UUID
    ) -> GalleryItemResponse | None:
        """
        @brief Hook used by post-creation flow: add media to user's default gallery.

        Idempotent — silently skips if media already in the gallery.
        """
        default = await self._repo.get_default_for_user(self._community_id, user_id)
        if default is None:
            ensured = await self.ensure_default_gallery(user_id)
            default = await self._repo.get_by_id(ensured.id, community_id=self._community_id)
        if default is None:
            return None
        existing = await self._repo.get_item(default.id, media_id)
        if existing is not None:
            return GalleryItemResponse.model_validate(existing)
        item = GalleryItem(
            community_id=self._community_id,
            gallery_id=default.id,
            media_id=media_id,
            added_by=user_id,
            position=default.item_count,
        )
        item = await self._repo.add_item(item)
        return GalleryItemResponse.model_validate(item)
