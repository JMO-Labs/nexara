"""
@file branding_service.py
@brief Business logic for community branding CRUD with Valkey caching.

Branding data is cached for 5 minutes in Valkey DB 2 and invalidated
on every admin update.
"""

from __future__ import annotations

import json
import uuid

import structlog
from redis.asyncio import Redis

from app.core.cache import DEFAULT_TTL, cache_delete, cache_get, cache_set
from app.core.i18n import _
from app.repositories.audit_repo import AuditRepository
from app.repositories.branding_repo import BrandingRepository
from app.schemas.branding import BrandingResponse, BrandingUpdate

logger = structlog.get_logger(__name__)


def _cache_key(community_id: uuid.UUID) -> str:
    """@brief Build the Valkey cache key for branding data."""
    return f"branding:{community_id}"


class BrandingService:
    """
    @brief Service layer for community branding operations.

    @param repo BrandingRepository instance.
    @param cache_client Async Redis client for Valkey DB 2 (or None).
    @param community_id UUID of the community scope.
    @param audit_repo Optional AuditRepository for logging admin actions.
    """

    def __init__(
        self,
        repo: BrandingRepository,
        cache_client: Redis | None = None,
        community_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self._repo = repo
        self._cache = cache_client
        self._community_id = community_id
        self._audit = audit_repo

    async def get_branding(self) -> BrandingResponse:
        """
        @brief Return branding data, serving from cache when available.

        Cache-aside pattern: check Valkey first, fall through to Postgres
        on miss, then write back to cache.

        @return BrandingResponse with current branding values.
        """
        key = _cache_key(self._community_id)

        if self._cache is not None:
            cached = await cache_get(self._cache, key)
            if cached is not None:
                data = json.loads(cached)
                return BrandingResponse(**data)

        row = await self._repo.get(self._community_id)
        if row is None:
            response = BrandingResponse(
                community_name="Nexara",
                color_primary="#3b82f6",
                color_primary_dark="#2563eb",
            )
        else:
            response = BrandingResponse(
                community_name=row.community_name,
                tagline=row.tagline,
                color_primary=row.color_primary,
                color_primary_dark=row.color_primary_dark,
                logo_light_url=None,
                logo_dark_url=None,
            )

        if self._cache is not None:
            await cache_set(self._cache, key, response.model_dump_json(), DEFAULT_TTL)

        return response

    async def update_branding(
        self,
        *,
        user_id: uuid.UUID,
        data: BrandingUpdate,
        ip_address: str | None = None,
    ) -> BrandingResponse:
        """
        @brief Update branding, invalidate cache, and write an audit entry.

        @param user_id UUID of the admin performing the update.
        @param data Validated branding update payload.
        @param ip_address Request originator IP for audit log.
        @return Updated BrandingResponse.
        """
        update_dict = data.model_dump(exclude_none=True)
        update_dict["updated_by"] = user_id

        row = await self._repo.upsert(self._community_id, update_dict)

        key = _cache_key(self._community_id)
        if self._cache is not None:
            await cache_delete(self._cache, key)

        if self._audit is not None:
            await self._audit.append(
                actor_id=user_id,
                action="branding.updated",
                target_type="branding",
                target_id=row.id,
                extra_data={"fields": list(update_dict.keys())},
                ip_address=ip_address,
            )

        logger.info("branding_updated", user_id=str(user_id), fields=list(update_dict.keys()))

        return BrandingResponse(
            community_name=row.community_name,
            tagline=row.tagline,
            color_primary=row.color_primary,
            color_primary_dark=row.color_primary_dark,
            logo_light_url=None,
            logo_dark_url=None,
        )
