"""
@file test_subgroup_media.py
@brief Integration tests for GET /api/v1/subgroups/{slug}/media endpoint.

Tests aggregation of media from posts, galleries, and events with source filtering
and pagination.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user


def _make_mock_user(user_id: uuid.UUID | None = None) -> MagicMock:
    """@brief Create a mock User for dependency injection."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.email = "test@example.com"
    user.username = "testuser"
    user.display_name = "Test User"
    user.role = "member"
    user.is_active = True
    return user


def _make_mock_subgroup(
    sg_id: uuid.UUID | None = None,
    is_private: bool = False,
) -> MagicMock:
    """@brief Create a mock Subgroup."""
    sg = MagicMock()
    sg.id = sg_id or uuid.uuid4()
    sg.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    sg.name = "Family"
    sg.slug = "family"
    sg.is_private = is_private
    sg.created_at = datetime.now(UTC)
    sg.updated_at = datetime.now(UTC)
    return sg


class TestSubgroupMedia:
    """@brief GET /api/v1/subgroups/{slug}/media endpoint tests."""

    @pytest.mark.asyncio
    async def test_list_media_all_sources(self, test_app):
        """@brief GET /media returns aggregated media from all sources."""
        user_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        sg_id = uuid.uuid4()
        mock_sg = _make_mock_subgroup(sg_id=sg_id)

        media_items = [
            {
                "media_id": str(uuid.uuid4()),
                "media": {
                    "id": str(uuid.uuid4()),
                    "filename": "photo.jpg",
                    "content_type": "image/jpeg",
                    "storage_key": "key1",
                    "thumbnail_key": None,
                    "size_bytes": 1024,
                    "width": 800,
                    "height": 600,
                    "duration_secs": None,
                    "alt_text": None,
                    "status": "ready",
                    "created_at": "2025-04-28T10:00:00+00:00",
                },
                "source": "post",
                "source_id": str(uuid.uuid4()),
                "source_title": "A nice photo",
                "created_at": "2025-04-28T10:00:00+00:00",
            }
        ]

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with (
                patch("app.api.v1.subgroups.SubgroupService") as mock_service_cls,
                patch("app.api.v1.subgroups.SubgroupMediaService") as mock_media_service_cls,
            ):
                mock_service = AsyncMock()
                mock_service.get_subgroup = AsyncMock(return_value=mock_sg)
                mock_service_cls.return_value = mock_service

                mock_media_service = AsyncMock()
                mock_media_service.list_media = AsyncMock(return_value=(media_items, None))
                mock_media_service_cls.return_value = mock_media_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get(
                        f"/api/v1/subgroups/{mock_sg.slug}/media?source=all&limit=60"
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["source"] == "post"
            assert data["next_cursor"] is None
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_media_filter_by_source(self, test_app):
        """@brief GET /media?source=gallery filters by gallery source."""
        user_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        sg_id = uuid.uuid4()
        mock_sg = _make_mock_subgroup(sg_id=sg_id)

        media_items = [
            {
                "media_id": str(uuid.uuid4()),
                "media": {
                    "id": str(uuid.uuid4()),
                    "filename": "vacation.jpg",
                    "content_type": "image/jpeg",
                    "storage_key": "key2",
                    "thumbnail_key": None,
                    "size_bytes": 2048,
                    "width": 1024,
                    "height": 768,
                    "duration_secs": None,
                    "alt_text": None,
                    "status": "ready",
                    "created_at": "2025-04-27T10:00:00+00:00",
                },
                "source": "gallery",
                "source_id": str(uuid.uuid4()),
                "source_title": "Summer Vacation",
                "created_at": "2025-04-27T10:00:00+00:00",
            }
        ]

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with (
                patch("app.api.v1.subgroups.SubgroupService") as mock_service_cls,
                patch("app.api.v1.subgroups.SubgroupMediaService") as mock_media_service_cls,
            ):
                mock_service = AsyncMock()
                mock_service.get_subgroup = AsyncMock(return_value=mock_sg)
                mock_service_cls.return_value = mock_service

                mock_media_service = AsyncMock()
                mock_media_service.list_media = AsyncMock(return_value=(media_items, None))
                mock_media_service_cls.return_value = mock_media_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get(
                        f"/api/v1/subgroups/{mock_sg.slug}/media?source=gallery&limit=20"
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["source"] == "gallery"
            # Verify the service was called with correct source
            call_kwargs = mock_media_service.list_media.call_args[1]
            assert call_kwargs["source"] == "gallery"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_media_pagination_cursor(self, test_app):
        """@brief GET /media?cursor=... uses pagination cursor."""
        user_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        sg_id = uuid.uuid4()
        mock_sg = _make_mock_subgroup(sg_id=sg_id)

        cursor = "2025-04-28T10:00:00+00:00:550e8400-e29b-41d4-a716-446655440000"
        next_cursor = "2025-04-27T10:00:00+00:00:550e8400-e29b-41d4-a716-446655440001"

        media_items = []  # Empty for simplicity

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with (
                patch("app.api.v1.subgroups.SubgroupService") as mock_service_cls,
                patch("app.api.v1.subgroups.SubgroupMediaService") as mock_media_service_cls,
            ):
                mock_service = AsyncMock()
                mock_service.get_subgroup = AsyncMock(return_value=mock_sg)
                mock_service_cls.return_value = mock_service

                mock_media_service = AsyncMock()
                mock_media_service.list_media = AsyncMock(return_value=(media_items, next_cursor))
                mock_media_service_cls.return_value = mock_media_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get(
                        f"/api/v1/subgroups/{mock_sg.slug}/media",
                        params={"cursor": cursor, "limit": 30},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data["next_cursor"] == next_cursor
            # Verify cursor was passed to service
            call_kwargs = mock_media_service.list_media.call_args[1]
            assert call_kwargs["cursor"] == cursor
            assert call_kwargs["limit"] == 30
        finally:
            test_app.dependency_overrides.clear()
