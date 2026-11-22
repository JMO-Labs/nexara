"""
@file features_service.py
@brief Read and update a community's feature flags; updates are audited.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.features import FEATURE_DEFAULTS
from app.repositories.community_repo import CommunityRepository


class FeaturesService:
    """@brief Effective feature flags for one community."""

    def __init__(
        self,
        communities: CommunityRepository,
        community_id: uuid.UUID,
        audit_repo: Any | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        self._communities = communities
        self._cid = community_id
        self._audit = audit_repo
        self._actor_id = actor_id
        self._ip = ip_address

    async def get(self) -> dict[str, bool]:
        """@return Every key mapped to its effective value."""
        community = await self._communities.get(self._cid)
        if community is None:
            raise NotFoundError()
        stored = community.features or {}
        return {k: bool(stored.get(k, d)) for k, d in FEATURE_DEFAULTS.items()}

    async def update(self, patch: dict[str, bool]) -> dict[str, bool]:
        """
        @param patch Partial ``{key: bool}``; keys must be known.
        @return Effective flags after the change.
        """
        await self._communities.update_features(self._cid, patch)
        if self._audit is not None and patch:
            await self._audit.append(
                actor_id=self._actor_id,
                action="features.updated",
                target_type="community",
                target_id=self._cid,
                extra_data={"changes": patch},
                ip_address=self._ip,
            )
        return await self.get()
