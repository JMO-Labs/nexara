"""
@file search_service.py
@brief Business logic for full-text search across posts, users, and events.

Sanitizes user input for tsquery, executes parallel searches by type,
and aggregates results into the SearchResponse schema.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from typing import TYPE_CHECKING

from app.repositories.search_repo import SearchRepository
from app.schemas.search import (
    SearchResultItem,
    SearchResponse,
    SearchTypeResults,
)

if TYPE_CHECKING:
    from app.models.user import User


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

    @param search_repo SearchRepository instance.
    @param community_id UUID of the community scope.
    """

    def __init__(
        self,
        search_repo: SearchRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = search_repo
        self._community_id = community_id

    @staticmethod
    def to_safe_tsquery(raw_input: str) -> str:
        """
        @brief Sanitize user input for PostgreSQL tsquery.

        Strips special chars that break tsquery (parentheses, &, |, !, :).
        Converts spaces to & (AND). Handles quoted phrases with <-> (proximity).
        Returns empty string if nothing remains after sanitization.

        @param raw_input Raw search string from the user.
        @return Safe tsquery string or empty string.
        """
        raw = (raw_input or "").strip()
        if not raw:
            return ""

        quoted = re.findall(r'"([^"]+)"', raw)
        rest = re.sub(r'"[^"]*"', " ", raw)
        rest = re.sub(r"[()&|!:*'\"]", " ", rest)
        words = [w for w in rest.split() if len(w) >= 2]
        for w in words:
            if not w.replace("_", "").isalnum():
                words = [x for x in words if x != w]

        parts: list[str] = []
        for phrase in quoted:
            phrase_words = [w for w in phrase.split() if len(w) >= 2]
            if phrase_words:
                parts.append(" <-> ".join(phrase_words))
        if words:
            parts.append(" & ".join(words))

        result = " & ".join(parts).strip()
        return result if result else ""

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
        @param content_types Requested types: posts, users, events.
        @param cursor Pagination cursor.
        @param limit Max items per type.
        @return SearchResponse with results grouped by type.
        """
        query_ts = self.to_safe_tsquery(query)
        if not query_ts:
            return SearchResponse(
                query=query,
                results={
                    t: SearchTypeResults(items=[], total=0, next_cursor=None)
                    for t in content_types
                },
            )

        tasks: list[tuple[str, object]] = []
        if "posts" in content_types:
            tasks.append(("posts", self._repo.search_posts(
                query_ts, self._community_id, user.id, cursor, limit
            )))
        if "users" in content_types:
            tasks.append(("users", self._repo.search_users(
                query_ts, self._community_id, cursor, limit
            )))
        if "events" in content_types:
            tasks.append(("events", self._repo.search_events(
                query_ts, self._community_id, cursor, limit
            )))

        coros = [t[1] for t in tasks]
        type_names = [t[0] for t in tasks]
        raw_results = await asyncio.gather(*coros)

        results: dict[str, SearchTypeResults] = {}
        for name, (rows, next_cursor, total) in zip(type_names, raw_results):
            if name == "posts":
                items = [
                    SearchResultItem(
                        id=p.id,
                        type="posts",
                        title=_snippet(p.content, 80),
                        snippet=_snippet(p.content),
                        created_at=p.created_at,
                    )
                    for p, _ in rows
                ]
            elif name == "users":
                items = [
                    SearchResultItem(
                        id=u.id,
                        type="users",
                        title=u.display_name or u.username,
                        snippet=_snippet(u.bio),
                        created_at=u.created_at,
                    )
                    for u, _ in rows
                ]
            else:
                items = [
                    SearchResultItem(
                        id=e.id,
                        type="events",
                        title=e.title,
                        snippet=_snippet(e.description),
                        created_at=e.created_at,
                    )
                    for e, _ in rows
                ]
            results[name] = SearchTypeResults(items=items, total=total, next_cursor=next_cursor)

        return SearchResponse(query=query, results=results)
