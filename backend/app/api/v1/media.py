"""
@file media.py
@brief Media API endpoints — upload, metadata, file serving, and delete.

All endpoints except thumbnail require authentication. Thumbnails are
served with cache headers for CDN efficiency.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.comment_repo import ReactionRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.user_repo import UserRepository
from app.schemas.media import (
    MediaResponse,
    MultipartCompleteResponse,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartPartResponse,
)
from app.schemas.post import ReactionResponse, ReactionToggle
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
    valkey = get_pool(settings, DB_CACHE)
    return MediaService(
        media_repo=MediaRepository(db),
        storage_backend=storage,
        user_repo=UserRepository(db),
        community_id=community_id,
        valkey_client=valkey,
    )


@router.post("/upload/init", response_model=MultipartInitResponse, status_code=201)
async def init_multipart_upload(
    body: MultipartInitRequest,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> MultipartInitResponse:
    """@brief Initialize a multipart upload session for large files (e.g. video)."""
    result = await service.init_multipart_upload(
        user=user,
        filename=body.filename,
        content_type=body.content_type,
        total_size=body.total_size,
    )
    return MultipartInitResponse(
        upload_id=result["upload_id"],
        part_size=result["part_size"],
    )


@router.put("/upload/{upload_id}/part/{part_number}", response_model=MultipartPartResponse)
async def upload_part(
    upload_id: str,
    part_number: int,
    request: Request,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> MultipartPartResponse:
    """@brief Upload a single part of a multipart upload (binary body)."""
    body = await request.body()
    result = await service.upload_part(
        upload_id=upload_id,
        part_number=part_number,
        data=bytes(body),
    )
    return MultipartPartResponse(
        part_number=result["part_number"],
        etag=result["etag"],
    )


@router.post("/upload/{upload_id}/complete", response_model=MultipartCompleteResponse)
async def complete_multipart_upload(
    upload_id: str,
    user: User = Depends(get_current_user),
    service: MediaService = Depends(_build_service),
) -> MultipartCompleteResponse:
    """@brief Complete multipart upload, assemble parts, create media record."""
    media = await service.complete_multipart_upload(
        upload_id=upload_id,
        user=user,
    )
    return MultipartCompleteResponse(media_id=media.id)


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
    service: MediaService = Depends(_build_service),
) -> StreamingResponse:
    """
    @brief Serve the original file with Cache-Control headers.

    Public endpoint — auth is enforced at upload/post level, not on serving.
    Consistent with the thumbnail endpoint.
    """
    content, content_type = await service.get_file_public(media_id)
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


@router.post("/{media_id}/reactions", response_model=ReactionResponse)
async def toggle_media_reaction(
    media_id: uuid.UUID,
    body: ReactionToggle,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MediaService = Depends(_build_service),
    community_id: uuid.UUID = Depends(_community_id),
) -> ReactionResponse:
    """
    @brief Toggle a reaction on media (add or remove).

    Validates media exists. Uses ReactionRepository.toggle with target_type="media".
    """
    await service.get_metadata(media_id)
    reaction_repo = ReactionRepository(db)
    action, count = await reaction_repo.toggle(
        user_id=user.id,
        target_type="media",
        target_id=media_id,
        emoji=body.emoji,
        community_id=community_id,
    )
    return ReactionResponse(action=action, emoji=body.emoji, count=count)
