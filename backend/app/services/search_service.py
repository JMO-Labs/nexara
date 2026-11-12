"""
@file search_service.py
@brief Business logic for full-text search across posts, users, events, and comments.

Delegates query parsing to PostgreSQL's websearch_to_tsquery (via the repository),
executes parallel searches by type, and aggregates results into the SearchResponse
schema.  Prefix matching is provided via to_tsquery with the :* operator so that
partial words (e.g. "app") match stemmed lexemes (e.g. "appl" from "apple").
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from typing import TYPE_CHECKING, Any

from app.core.cache import cache_get, cache_set
from app.core.metrics import search_cache_hits_total, search_cache_misses_total
from app.repositories.search_repo import SearchRepository
from app.schemas.search import (
    SearchResponse,
    SearchResultItem,
    SearchTypeResults,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.models.user import User

_UNSAFE_CHARS = re.compile(r"[^\w\s]", re.UNICODE)

SEARCH_CACHE_TTL: int = 60
"""@brief Search cache TTL in seconds (reset on hit)."""


def search_cache_key(
    query: str,
    community_id: uuid.UUID,
    content_types: list[str],
    user_id: uuid.UUID,
    cursor: str | None,
) -> str:
    """
    @brief Build the deterministic cache key ``search:{sha256}:{cursor}``.

    The hash covers the normalized query, community, sorted types and the
    viewer id (results are visibility/block filtered per user).

    @return Cache key; cursor defaults to ``0`` for the first page.
    """
    normalized = " ".join(query.lower().split())
    raw = "|".join([normalized, str(community_id), ",".join(sorted(content_types)), str(user_id)])
    return f"search:{hashlib.sha256(raw.encode()).hexdigest()}:{cursor or '0'}"


def build_prefix_tsquery(raw: str) -> str:
    """
    @brief Build a PostgreSQL tsquery string with prefix matching on every term.

    Each word is suffixed with :* so ``to_tsquery('english', ...)`` performs
    prefix matching against the GIN index.  Words shorter than 2 characters
    are dropped to avoid overly broad matches.

    @param raw  Raw user input (may contain special chars).
    @return     tsquery string like ``"hello:* & world:*"``, or ``""``
                if no usable words remain.
    """
    cleaned = _UNSAFE_CHARS.sub(" ", raw)
    words = [w for w in cleaned.split() if len(w) >= 2]
    if not words:
        return ""
    return " & ".join(f"{w}:*" for w in words)


def _snippet(content: str | None, max_len: int = 150) -> str:
    """
    @brief Truncate content to a short snippet for search preview.

    @param content Full text content.
    @param max_len Maximum snippet length.
    @return Truncated string with ellipsis if needed.
    """
    if not content:
        return ""
    text = content.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


class SearchService:
    """
    @brief Service layer for unified search across content types.

    Raw user queries are passed directly to the repository layer, which
    uses PostgreSQL websearch_to_tsquery for robust parsing of user input
    including quoted phrases, stop words, hyphens, and operators.

    @param search_repo SearchRepository instance.
    @param community_id UUID of the community scope.
    @param cache_client Optional Valkey client for first-page caching.
    """

    def __init__(
        self,
        search_repo: SearchRepository,
        community_id: uuid.UUID,
        cache_client: Redis | None = None,
    ) -> None:
        self._repo = search_repo
        self._community_id = community_id
        self._cache = cache_client

    async def search(
        self,
        query: str,
        user: User,
        content_types: list[str],
        cursor: str | None,
        limit: int,
    ) -> SearchResponse:
        """
        @brief Execute search across requested content types.

        @param query Raw search query (min 2 chars, validated by API).
        @param user Current authenticated user (for block filter).
        @param content_types Requested types: posts, users, events, comments.
        @param cursor Pagination cursor.
        @param limit Max items per type.
        @return SearchResponse with results grouped by type.
        """
        q = (query or "").strip()
        if not q:
            return SearchResponse(
                query=query,
                results={
                    t: SearchTypeResults(items=[], total=0, next_cursor=None) for t in content_types
                },
            )

        cache_key: str | None = None
        if self._cache is not None and cursor in (None, "0"):
            cache_key = search_cache_key(q, self._community_id, content_types, user.id, cursor)
            cached = await cache_get(self._cache, cache_key)
            if cached is not None:
                try:
                    hit = SearchResponse.model_validate_json(cached)
                except ValueError:
                    hit = None
                if hit is not None:
                    search_cache_hits_total.labels(community_id=str(self._community_id)).inc()
                    try:
                        await self._cache.expire(cache_key, SEARCH_CACHE_TTL)
                    except Exception:  # noqa: BLE001
                        pass
                    return hit
            search_cache_misses_total.labels(community_id=str(self._community_id)).inc()

        response = await self._query(q, query, user, content_types, cursor, limit)
        if cache_key is not None and self._cache is not None:
            await cache_set(
                self._cache,
                cache_key,
                json.dumps(response.model_dump(mode="json")),
                ttl=SEARCH_CACHE_TTL,
            )
        return response

    async def _query(
        self,
        q: str,
        query: str,
        user: User,
        content_types: list[str],
        cursor: str | None,
        limit: int,
    ) -> SearchResponse:
        """@brief Run the repository searches and build the response."""
        prefix_q = build_prefix_tsquery(q)

        tasks: list[tuple[str, object]] = []
        if "posts" in content_types:
            tasks.append(
                (
                    "posts",
                    self._repo.search_posts(
                        q,
                        prefix_q,
                        self._community_id,
                        user.id,
                        cursor,
                        limit,
                    ),
                )
            )
        if "users" in content_types:
            tasks.append(
                (
                    "users",
                    self._repo.search_users(
                        q,
                        prefix_q,
                        self._community_id,
                        cursor,
                        limit,
                    ),
                )
            )
        if "events" in content_types:
            tasks.append(
                (
                    "events",
                    self._repo.search_events(
                        q,
                        prefix_q,
                        self._community_id,
                        cursor,
                        limit,
                    ),
                )
            )
        if "subgroups" in content_types:
            tasks.append(
                (
                    "subgroups",
                    self._repo.search_subgroups(
                        q,
                        prefix_q,
                        self._community_id,
                        user.id,
                        cursor,
                        limit,
                    ),
                )
            )
        if "comments" in content_types:
            tasks.append(
                (
                    "comments",
                    self._repo.search_comments(
                        q,
                        prefix_q,
                        self._community_id,
                        user.id,
                        cursor,
                        limit,
                    ),
                )
            )

        coros = [t[1] for t in tasks]
        type_names = [t[0] for t in tasks]
        raw_results = await asyncio.gather(*coros)  # type: ignore[call-overload]

        results: dict[str, SearchTypeResults] = {}
        for name, (rows, next_cursor, total) in zip(type_names, raw_results):
            items = self._format_results(name, rows)
            results[name] = SearchTypeResults(items=items, total=total, next_cursor=next_cursor)

        return SearchResponse(query=query, results=results)

    @staticmethod
    def _format_results(result_type: str, rows: list[tuple[Any, float]]) -> list[SearchResultItem]:
        """
        @brief Convert raw DB rows into SearchResultItem list.

        @param result_type Content type name (posts, users, events, comments).
        @param rows List of (model, rank) tuples from the repository.
        @return List of SearchResultItem.
        """
        items: list[SearchResultItem] = []
        for entity, _rank in rows:
            if result_type == "posts":
                items.append(
                    SearchResultItem(
                        id=entity.id,
                        type="posts",
                        title=_snippet(entity.content, 80),
                        snippet=_snippet(entity.content),
                        created_at=entity.created_at,
                    )
                )
            elif result_type == "users":
                items.append(
                    SearchResultItem(
                        id=entity.id,
                        type="users",
                        title=entity.display_name or entity.username,
                        snippet=_snippet(entity.bio),
                        created_at=entity.created_at,
                    )
                )
            elif result_type == "events":
                items.append(
                    SearchResultItem(
                        id=entity.id,
                        type="events",
                        title=entity.title,
                        snippet=_snippet(entity.description),
                        created_at=entity.created_at,
                    )
                )
            elif result_type == "subgroups":
                items.append(
                    SearchResultItem(
                        id=entity.id,
                        type="subgroups",
                        title=entity.name,
                        snippet=_snippet(entity.description),
                        created_at=entity.created_at,
                        slug=entity.slug,
                    )
                )
            elif result_type == "comments":
                items.append(
                    SearchResultItem(
                        id=entity.id,
                        type="comments",
                        title=_snippet(entity.content, 80),
                        snippet=_snippet(entity.content),
                        created_at=entity.created_at,
                        parent_id=entity.post_id,
                    )
                )
        return items
