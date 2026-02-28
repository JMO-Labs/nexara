"""
@file media.py
@brief Media API endpoints — upload, metadata, file serving, and delete.

All endpoints except thumbnail require authentication. Thumbnails are
served with cache headers for CDN efficiency.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.schemas.media import MediaResponse
from app.services.media_service import MediaService
from app.services.storage.factory import get_storage_backend

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/media", tags=["media"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> MediaService:
    """@brief Build the MediaService with injected dependencies."""
    storage = get_storage_backend(settings)
    return MediaService(
        media_repo=MediaRepository(db),
        storage_backend=storage,
        user_repo=UserRepository(db),
        community_id=community_id,
    )


@router.post("/upload", response_model=MediaResponse, status_code=201)
async def upload_media(
    file: UploadFile,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> MediaResponse:
    """
    @brief Upload an image file (multipart/form-data).

    Accepts JPEG, PNG, GIF, WebP up to 20 MB. Enqueues thumbnail generation.
    """
    content_type = file.content_type or "application/octet-stream"
    file_data = await file.read()
    size = len(file_data)
    filename = file.filename or "upload"
    return await service.upload(
        user=user,
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        size=size,
    )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media_metadata(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> MediaResponse:
    """@brief Return media metadata by ID."""
    return await service.get_metadata(media_id)


@router.get("/{media_id}/file")
async def get_media_file(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> StreamingResponse:
    """
    @brief Serve the original file with Cache-Control headers.

    Returns the raw file bytes with appropriate content type.
    """
    content, content_type = await service.get_file(media_id, user)
    return StreamingResponse(
        iter([content]),
        media_type=content_type,
        headers={
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": "inline",
        },
    )


@router.get("/{media_id}/thumbnail")
async def get_media_thumbnail(
    media_id: uuid.UUID,
    service: MediaService = Depends(_build_service),
) -> StreamingResponse:
    """
    @brief Serve the thumbnail (public, no auth required).

    Returns WebP thumbnail with cache headers for CDN.
    """
    content, _ = await service.get_thumbnail(media_id)
    return StreamingResponse(
        iter([content]),
        media_type="image/webp",
        headers={
            "Cache-Control": "public, max-age=604800",
            "Content-Disposition": "inline",
        },
    )


@router.delete("/{media_id}", status_code=204)
async def delete_media(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> None:
    """@brief Delete media (owner only). Decrements user quota."""
    await service.delete(media_id, user)
