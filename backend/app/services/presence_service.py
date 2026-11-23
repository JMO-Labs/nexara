"""
@file presence_service.py
@brief Batch presence lookup honouring privacy flags, blocks and community.
"""

from __future__ import annotations

import uuid

from app.repositories.presence_repo import PresenceRepository
from app.schemas.presence import PresenceResponse
from app.services.realtime.presence import online_among


class PresenceService:
    """
    @brief Resolves presence for a list of users on behalf of a viewer.

    @param repo Presence repository.
    @param community_id Community scope.
    """

    def __init__(self, repo: PresenceRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._community_id = community_id

    async def lookup(self, viewer_id: uuid.UUID, ids: list[uuid.UUID]) -> PresenceResponse:
        """
        @brief Presence for ids; omitted users are blocked/other-community/inactive.
        @param viewer_id Viewing user (sees themselves regardless of flags).
        @param ids Requested ids (deduplicated).
        @return Online ids plus last_seen for users who share it.
        """
        rows = await self._repo.visible(viewer_id, self._community_id, list(set(ids)))
        live = await online_among([r.user_id for r in rows])
        online: list[uuid.UUID] = []
        last_seen = {}
        for r in rows:
            me = r.user_id == viewer_id
            if (me or r.show_online_status) and r.user_id in live:
                online.append(r.user_id)
            if me or r.show_last_seen:
                last_seen[r.user_id] = r.last_seen_at
        return PresenceResponse(online=online, last_seen=last_seen)
