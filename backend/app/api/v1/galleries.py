"""
@file galleries.py
@brief Galleries API — CRUD, items, collaborators, hub listing.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.gallery import (
    CollaboratorAdd,
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
from app.services.gallery_service import GalleryService
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/galleries", tags=["galleries"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> GalleryService:
    """@brief Build GalleryService with notification + DB deps."""
    notif = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        event_bus=event_bus,
    )
    return GalleryService(
        gallery_repo=GalleryRepository(db),
        community_id=community_id,
        session=db,
        notification_service=notif,
    )


# ── CRUD ──────────────────────────────────────────────────────────


@router.post("", response_model=GalleryResponse, status_code=201)
async def create_gallery(
    body: GalleryCreate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryResponse:
    """@brief Create a gallery."""
    return await service.create_gallery(user.id, body)


@router.get("", response_model=GalleryList)
async def list_galleries(
    q: str | None = None,
    owner_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    subgroup_id: uuid.UUID | None = None,
    featured_only: bool = False,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryList:
    """@brief Community gallery hub — search or list galleries visible to the viewer."""
    if q:
        return await service.search(
            q=q,
            viewer_id=user.id,
            limit=limit,
            offset=offset,
        )
    return await service.list_galleries(
        user.id,
        owner_id=owner_id,
        event_id=event_id,
        subgroup_id=subgroup_id,
        featured_only=featured_only,
        cursor=cursor,
        limit=limit,
    )


@router.get("/default", response_model=GalleryResponse)
async def get_default_gallery(
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryResponse:
    """@brief Get-or-create the user's default "All Photos" gallery."""
    return await service.ensure_default_gallery(user.id)


@router.get("/{gallery_id}", response_model=GalleryResponse)
async def get_gallery(
    gallery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryResponse:
    """@brief Get a gallery."""
    return await service.get_gallery(gallery_id, user.id)


@router.patch("/{gallery_id}", response_model=GalleryResponse)
async def update_gallery(
    gallery_id: uuid.UUID,
    body: GalleryUpdate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryResponse:
    """@brief Update a gallery (owner only)."""
    return await service.update_gallery(gallery_id, user.id, body)


@router.delete("/{gallery_id}", response_model=MessageResponse)
async def delete_gallery(
    gallery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete a gallery (owner only)."""
    await service.delete_gallery(gallery_id, user.id)
    return MessageResponse(message=_("Gallery deleted"))


# ── Items ─────────────────────────────────────────────────────────


@router.get("/{gallery_id}/items", response_model=list[GalleryItemResponse])
async def list_items(
    gallery_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> list[GalleryItemResponse]:
    """@brief List items in a gallery."""
    return await service.list_items(gallery_id, user.id, cursor=cursor, limit=limit)


@router.post("/{gallery_id}/items", response_model=GalleryItemResponse, status_code=201)
async def add_item(
    gallery_id: uuid.UUID,
    body: GalleryItemCreate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryItemResponse:
    """@brief Add a single media item to a gallery."""
    return await service.add_item(gallery_id, user.id, body)


@router.post(
    "/{gallery_id}/items/bulk",
    response_model=list[GalleryItemResponse],
    status_code=201,
)
async def bulk_add_items(
    gallery_id: uuid.UUID,
    body: GalleryItemBulkCreate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> list[GalleryItemResponse]:
    """@brief Add multiple media items in a single request."""
    return await service.bulk_add_items(gallery_id, user.id, body)


@router.patch("/{gallery_id}/items/{item_id}", response_model=GalleryItemResponse)
async def update_item(
    gallery_id: uuid.UUID,
    item_id: uuid.UUID,
    body: GalleryItemUpdate,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> GalleryItemResponse:
    """@brief Update an item's caption or position."""
    return await service.update_item(gallery_id, item_id, user.id, body)


@router.delete("/{gallery_id}/items/{item_id}", response_model=MessageResponse)
async def remove_item(
    gallery_id: uuid.UUID,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> MessageResponse:
    """@brief Remove an item from the gallery."""
    await service.remove_item(gallery_id, item_id, user.id)
    return MessageResponse(message=_("Item removed"))


# ── Collaborators ─────────────────────────────────────────────────


@router.get("/{gallery_id}/collaborators", response_model=list[CollaboratorResponse])
async def list_collaborators(
    gallery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> list[CollaboratorResponse]:
    """@brief List collaborators."""
    return await service.list_collaborators(gallery_id, user.id)


@router.post(
    "/{gallery_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=201,
)
async def add_collaborator(
    gallery_id: uuid.UUID,
    body: CollaboratorAdd,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> CollaboratorResponse:
    """@brief Invite a collaborator."""
    return await service.add_collaborator(gallery_id, user.id, body.user_id)


@router.delete(
    "/{gallery_id}/collaborators/{target_user_id}",
    response_model=MessageResponse,
)
async def remove_collaborator(
    gallery_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: GalleryService = Depends(_build_service),
) -> MessageResponse:
    """@brief Remove a collaborator."""
    await service.remove_collaborator(gallery_id, user.id, target_user_id)
    return MessageResponse(message=_("Collaborator removed"))
