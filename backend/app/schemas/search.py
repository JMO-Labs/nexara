"""
@file search.py
@brief Pydantic schemas for search requests and responses.

Used by the search API endpoint and service layer for validation
and serialization of search queries and result sets.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    @brief Query parameters for GET /api/v1/search/.

    @param q Search query string (min 2 chars).
    @param types Comma-separated content types: posts, users, events.
    @param cursor Opaque cursor for pagination.
    @param limit Max items per type (default 20).
    """

    q: str = Field(..., min_length=2)
    types: str | None = Field(default=None, description="Comma-separated: posts,users,events")
    cursor: str | None = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)


class SearchResultItem(BaseModel):
    """
    @brief Single search result item across posts, users, events, or comments.

    @param id UUID of the entity.
    @param type Content type: "posts", "users", "events", or "comments".
    @param title Display title (post snippet, display_name, event title).
    @param snippet Excerpt or summary for preview.
    @param created_at When the entity was created.
    @param parent_id Optional parent entity UUID (e.g. post_id for comments).
    """

    id: UUID
    type: str
    title: str
    snippet: str
    created_at: datetime
    parent_id: UUID | None = None

    model_config = {"from_attributes": True}


class SearchTypeResults(BaseModel):
    """
    @brief Paginated results for a single content type.

    @param items List of SearchResultItem for this type.
    @param total Total count matching the query.
    @param next_cursor Cursor for next page, or None if no more.
    """

    items: list[SearchResultItem]
    total: int
    next_cursor: str | None = None


class SearchResponse(BaseModel):
    """
    @brief Full search response with results grouped by type.

    @param query The original search query.
    @param results Dict mapping type name to SearchTypeResults.
    """

    query: str
    results: dict[str, SearchTypeResults]
