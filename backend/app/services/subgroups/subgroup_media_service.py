"""
@file subgroup_media_service.py
@brief Service for aggregated subgroup media retrieval.

Handles authorization and delegates to SubgroupMediaRepository for
union queries across posts, galleries, and events.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository


class SubgroupMediaService:
    """@brief Service for listing aggregated media in a subgroup."""

    def __init__(
        self,
        subgroup_repo: SubgroupRepository,
        media_repo: SubgroupMediaRepository,
        community_id: uuid.UUID,
    ) -> None:
        """@brief Initialize with repos and community context."""
        self._subgroup_repo = subgroup_repo
        self._media_repo = media_repo
        self._community_id = community_id

    async def list_media(
        self,
        *,
        subgroup_id: uuid.UUID,
        viewer_id: uuid.UUID,
        source: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        @brief List media aggregated from posts, galleries, and events in a subgroup.

        @param subgroup_id ID of the subgroup.
        @param viewer_id Requesting user ID for auth checks.
        @param source Filter: 'post', 'gallery', 'event', or 'all' (default).
        @param cursor Keyset pagination cursor (ISO timestamp:uuid).
        @param limit Number of items (clamped to 200).
        @return Tuple of (media items, next_cursor).
        @raises NotFoundError If subgroup does not exist.
        @raises AuthorizationError If viewer cannot access the subgroup.
        """
        # Fetch and validate subgroup
        subgroup = await self._subgroup_repo.get_by_id(subgroup_id)
        if not subgroup:
            raise NotFoundError("Subgroup not found")

        # Check membership for private subgroups
        if subgroup.is_private:
            is_member = await self._subgroup_repo.is_member(subgroup_id, viewer_id)
            if not is_member:
                raise AuthorizationError("Not a member of this subgroup")

        # Delegate to media repo for the actual query
        limit = min(limit, 200)
        items, next_cursor = await self._media_repo.list_media(
            subgroup_id=subgroup_id,
            viewer_id=viewer_id,
            source=source,
            cursor=cursor,
            limit=limit,
        )

        return items, next_cursor
