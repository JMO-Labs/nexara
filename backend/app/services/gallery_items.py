"""
@file gallery_items.py
@brief Gallery items, collaborators and auto-population (mixin).
"""

from __future__ import annotations

import uuid

import structlog

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.models.user import User
from app.schemas.gallery import (
    CollaboratorResponse,
    GalleryItemBulkCreate,
    GalleryItemCreate,
    GalleryItemResponse,
    GalleryItemUpdate,
    GalleryResponse,
)
from app.services.gallery_base import GalleryServiceBase

logger = structlog.get_logger(__name__)


class GalleryItemsMixin(GalleryServiceBase):
    """@brief Item, collaborator and auto-population operations for galleries."""

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

    async def _actor_name(self, user_id: uuid.UUID) -> str:
        """@brief Display name of ``user_id`` for notification payloads."""
        user = await self._session.get(User, user_id)
        return str(user.display_name) if user is not None else _("Someone")

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
                        "actor_name": await self._actor_name(user_id),
                        "gallery_title": gallery.title,
                        "activity": "invited",
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
