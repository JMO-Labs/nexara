"""
@file search.py
@brief Search API endpoint — full-text search across posts, users, events, and comments.

GET /api/v1/search/?q=...&types=posts,users,events,comments&cursor=...&limit=20
Requires authentication. Returns 422 for empty or too-short query.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AppError
from app.core.i18n import _
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.search_repo import SearchRepository
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])
"""@brief Search router for full-text search across content types."""


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> SearchService:
    """@brief Build the SearchService with injected dependencies."""
    try:
        cache: Redis | None = get_pool(settings, DB_CACHE)
    except Exception:  # noqa: BLE001
        cache = None
    return SearchService(
        search_repo=SearchRepository(db),
        community_id=community_id,
        cache_client=cache,
    )


"""@brief All valid search content types."""
_ALL_TYPES = ["posts", "users", "events", "subgroups", "comments", "galleries", "polls"]
_VALID_TYPES = set(_ALL_TYPES)


def _parse_types(types_str: str | None) -> list[str]:
    """
    @brief Parse comma-separated types string into list.

    @param types_str Raw types param (e.g. "posts,users,events,comments").
    @return List of valid type names; defaults to all if empty.
    """
    if not types_str or not types_str.strip():
        return _ALL_TYPES
    raw = [t.strip().lower() for t in types_str.split(",")]
    return [t for t in raw if t in _VALID_TYPES] or _ALL_TYPES


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query (min 2 characters)"),
    types: str | None = Query(
        default=None,
        description="Comma-separated: posts,users,events,subgroups,comments,galleries,polls",
    ),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: SearchService = Depends(_build_service),
) -> SearchResponse:
    """
    @brief Full-text search across posts, users, events, and comments.

    Query must be at least 2 characters. Returns 422 for empty or
    too-short query. Results are grouped by content type.
    """
    q_stripped = (q or "").strip()
    if not q_stripped:
        raise AppError(
            code="VALIDATION_ERROR",
            message=_("Search query cannot be empty."),
            status_code=422,
        )
    if len(q_stripped) < 2:
        raise AppError(
            code="VALIDATION_ERROR",
            message=_("Search query must be at least 2 characters."),
            status_code=422,
        )

    content_types = _parse_types(types)
    return await service.search(
        query=q_stripped,
        user=user,
        content_types=content_types,
        cursor=cursor,
        limit=limit,
    )
