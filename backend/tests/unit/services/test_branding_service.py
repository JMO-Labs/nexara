"""
@file test_branding_service.py
@brief Unit tests for BrandingService.

Tests verify caching, cache invalidation, hex color validation,
and audit logging behaviour using mocked dependencies.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.branding import BrandingUpdate


COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_USER_ID = uuid.uuid4()


def _make_branding_row():
    """@brief Create a mock CommunityBranding ORM object."""
    row = MagicMock()
    row.community_name = "Nexara"
    row.tagline = "A community platform"
    row.color_primary = "#3b82f6"
    row.color_primary_dark = "#2563eb"
    row.logo_light_media_id = None
    row.logo_dark_media_id = None
    return row


class TestGetBranding:
    """@brief Tests for BrandingService.get_branding()."""

    @pytest.mark.asyncio
    async def test_returns_cached_data_on_second_call(self):
        """get_branding should serve from Valkey cache on cache hit."""
        from app.services.branding_service import BrandingService

        mock_repo = AsyncMock()
        mock_cache = AsyncMock()
        cached_data = json.dumps({
            "community_name": "Cached",
            "tagline": None,
            "color_primary": "#3b82f6",
            "color_primary_dark": "#2563eb",
            "logo_light_url": None,
            "logo_dark_url": None,
        })
        mock_cache.get.return_value = cached_data

        service = BrandingService(
            repo=mock_repo, cache_client=mock_cache, community_id=COMMUNITY_ID,
        )
        result = await service.get_branding()

        assert result.community_name == "Cached"
        mock_repo.get.assert_not_awaited()


class TestUpdateBranding:
    """@brief Tests for BrandingService.update_branding()."""

    @pytest.mark.asyncio
    async def test_invalidates_cache_on_update(self):
        """update_branding should delete the cache key after persisting."""
        from app.services.branding_service import BrandingService

        mock_repo = AsyncMock()
        mock_repo.upsert.return_value = _make_branding_row()
        mock_cache = AsyncMock()
        mock_audit_repo = AsyncMock()

        service = BrandingService(
            repo=mock_repo, cache_client=mock_cache,
            community_id=COMMUNITY_ID, audit_repo=mock_audit_repo,
        )

        update = BrandingUpdate(community_name="Updated")
        await service.update_branding(
            user_id=ADMIN_USER_ID, data=update, ip_address="127.0.0.1",
        )

        mock_cache.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_writes_audit_log_entry(self):
        """update_branding should create an audit log entry."""
        from app.services.branding_service import BrandingService

        mock_repo = AsyncMock()
        mock_repo.upsert.return_value = _make_branding_row()
        mock_cache = AsyncMock()
        mock_audit_repo = AsyncMock()

        service = BrandingService(
            repo=mock_repo, cache_client=mock_cache,
            community_id=COMMUNITY_ID, audit_repo=mock_audit_repo,
        )

        update = BrandingUpdate(community_name="Updated")
        await service.update_branding(
            user_id=ADMIN_USER_ID, data=update, ip_address="127.0.0.1",
        )

        mock_audit_repo.append.assert_awaited_once()
        call_kwargs = mock_audit_repo.append.call_args.kwargs
        assert call_kwargs["action"] == "branding.updated"
        assert call_kwargs["actor_id"] == ADMIN_USER_ID


class TestColorValidation:
    """@brief Tests for BrandingUpdate hex color validation."""

    def test_valid_hex_color_accepted(self):
        """A valid #RRGGBB color should be accepted."""
        update = BrandingUpdate(color_primary="#ff5500")
        assert update.color_primary == "#ff5500"

    def test_invalid_hex_color_rejected(self):
        """An invalid color format should raise a validation error."""
        with pytest.raises(Exception):
            BrandingUpdate(color_primary="red")

    def test_short_hex_rejected(self):
        """A 3-digit hex shorthand should be rejected."""
        with pytest.raises(Exception):
            BrandingUpdate(color_primary="#f00")
