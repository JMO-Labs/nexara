"""
@file bookmarks.py
@brief Bookmark API endpoints: toggle, list, delete.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.bookmark_repo import BookmarkRepository
from app.repositories.post_repo import PostRepository
from app.schemas.bookmark import BookmarkList, BookmarkToggleResponse
from app.services.bookmark_service import BookmarkService

router = APIRouter(tags=["bookmarks"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookmarkService:
    """@brief Build BookmarkService with injected dependencies."""
    return BookmarkService(
        BookmarkRepository(db), PostRepository(db), uuid.UUID(settings.COMMUNITY_ID)
    )


@router.post("/posts/{post_id}/bookmark", response_model=BookmarkToggleResponse)
async def toggle_bookmark(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: BookmarkService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Toggle a bookmark on a post."""
    return await service.toggle(post_id, user.id)


@router.get("/bookmarks", response_model=BookmarkList)
async def list_bookmarks(
    user: User = Depends(get_current_user),
    service: BookmarkService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    """@brief List the current user's bookmarks."""
    return await service.list(user.id, cursor, limit)


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: BookmarkService = Depends(_build_service),
) -> Response:
    """@brief Delete a bookmark."""
    await service.delete(bookmark_id, user.id)
    return Response(status_code=204)
