"""
@file gallery_admin.py
@brief Admin moderation operations for galleries (mixin).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.schemas.gallery import GalleryResponse
from app.services.gallery_base import GalleryServiceBase

logger = structlog.get_logger(__name__)


class GalleryAdminMixin(GalleryServiceBase):
    """@brief Admin feature/visibility/delete operations with audit logging."""

    # ── Admin Moderation ──────────────────────────────────────────────

    async def admin_feature(
        self, gallery_id: uuid.UUID, featured: bool, admin_id: uuid.UUID
    ) -> GalleryResponse:
        """
        @brief Admin feature/unfeature a gallery and write audit log.

        @param gallery_id UUID of the gallery.
        @param featured Whether to feature the gallery.
        @param admin_id UUID of the admin performing the action.
        @return Updated GalleryResponse.
        @raises NotFoundError If the gallery is not found.
        """
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        old_featured = gallery.is_featured
        gallery = await self._repo.update(gallery, {"is_featured": featured})
        if self._audit_repo:
            await self._audit_repo.append(
                actor_id=admin_id,
                action="admin.gallery.featured",
                target_type="gallery",
                target_id=gallery_id,
                extra_data={"featured": featured, "was_featured": old_featured},
            )
        logger.info(
            "admin_gallery_featured",
            admin_id=str(admin_id),
            gallery_id=str(gallery_id),
            featured=featured,
        )
        return GalleryResponse.model_validate(gallery)

    async def admin_force_visibility(
        self, gallery_id: uuid.UUID, visibility: str, admin_id: uuid.UUID
    ) -> GalleryResponse:
        """
        @brief Admin force-change a gallery's visibility and write audit log.

        @param gallery_id UUID of the gallery.
        @param visibility New visibility level (community, subgroup, private).
        @param admin_id UUID of the admin performing the action.
        @return Updated GalleryResponse.
        @raises NotFoundError If the gallery is not found.
        """
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        old_visibility = gallery.visibility
        gallery = await self._repo.update(gallery, {"visibility": visibility})
        if self._audit_repo:
            await self._audit_repo.append(
                actor_id=admin_id,
                action="admin.gallery.visibility_changed",
                target_type="gallery",
                target_id=gallery_id,
                extra_data={"old_visibility": old_visibility, "new_visibility": visibility},
            )
        logger.info(
            "admin_gallery_visibility_changed",
            admin_id=str(admin_id),
            gallery_id=str(gallery_id),
            visibility=visibility,
        )
        return GalleryResponse.model_validate(gallery)

    async def admin_delete(self, gallery_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        """
        @brief Admin soft-delete a gallery and write audit log.

        @param gallery_id UUID of the gallery.
        @param admin_id UUID of the admin performing the action.
        @raises NotFoundError If the gallery is not found.
        """
        gallery = await self._repo.get_by_id(gallery_id, community_id=self._community_id)
        if gallery is None:
            raise NotFoundError(_("Gallery not found"))
        gallery = await self._repo.update(gallery, {"deleted_at": datetime.now(UTC)})
        if self._audit_repo:
            await self._audit_repo.append(
                actor_id=admin_id,
                action="admin.gallery.deleted",
                target_type="gallery",
                target_id=gallery_id,
                extra_data=None,
            )
        logger.info(
            "admin_gallery_deleted",
            admin_id=str(admin_id),
            gallery_id=str(gallery_id),
        )
