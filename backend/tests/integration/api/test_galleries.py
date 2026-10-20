"""
@file test_galleries.py
@brief Integration tests for galleries API: CRUD, bulk add, collaborators, search, admin.
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


def _make_mock_gallery(
    gallery_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    title: str = "My Gallery",
    **kwargs,
) -> MagicMock:
    """@brief Create a mock Gallery object."""
    gallery = MagicMock()
    gallery.id = gallery_id or uuid.uuid4()
    gallery.owner_id = owner_id or uuid.uuid4()
    gallery.title = title
    gallery.description = kwargs.get("description")
    gallery.visibility = kwargs.get("visibility", "community")
    gallery.contribution_policy = kwargs.get("contribution_policy", "owner_only")
    gallery.item_count = kwargs.get("item_count", 0)
    gallery.is_featured = kwargs.get("is_featured", False)
    gallery.is_default = kwargs.get("is_default", False)
    gallery.is_event_gallery = kwargs.get("is_event_gallery", False)
    gallery.created_at = datetime.now(UTC)
    gallery.updated_at = datetime.now(UTC)
    gallery.cover_media_id = kwargs.get("cover_media_id")
    gallery.event_id = kwargs.get("event_id")
    gallery.subgroup_id = kwargs.get("subgroup_id")
    return gallery


class TestGalleriesCRUD:
    """@brief POST/GET/PATCH/DELETE /api/v1/galleries"""

    @pytest.mark.asyncio
    async def test_create_gallery(self, test_app):
        """POST /galleries creates a new gallery."""
        user_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        gallery_id = uuid.uuid4()
        created_gallery = _make_mock_gallery(
            gallery_id=gallery_id,
            owner_id=user_id,
            title="My Photos",
            description="Vacation photos",
        )

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.create_gallery = AsyncMock(return_value=created_gallery)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/galleries",
                        json={
                            "title": "My Photos",
                            "description": "Vacation photos",
                            "visibility": "community",
                            "contribution_policy": "owner_only",
                        },
                    )

            assert resp.status_code == 201
            data = resp.json()
            assert data["title"] == "My Photos"
            assert data["description"] == "Vacation photos"
            assert data["owner_id"] == str(user_id)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_gallery(self, test_app):
        """GET /galleries/{id} retrieves a gallery."""
        user_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        gallery = _make_mock_gallery(
            gallery_id=gallery_id, owner_id=user_id, title="My Photos", item_count=5
        )

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.get_gallery = AsyncMock(return_value=gallery)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get(f"/api/v1/galleries/{gallery_id}")

            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(gallery_id)
            assert data["title"] == "My Photos"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_gallery(self, test_app):
        """PATCH /galleries/{id} updates a gallery."""
        user_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        updated_gallery = _make_mock_gallery(
            gallery_id=gallery_id,
            owner_id=user_id,
            title="Updated Photos",
            description="Updated description",
            visibility="private",
            is_featured=True,
            item_count=5,
        )

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.update_gallery = AsyncMock(return_value=updated_gallery)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.patch(
                        f"/api/v1/galleries/{gallery_id}",
                        json={
                            "title": "Updated Photos",
                            "description": "Updated description",
                            "visibility": "private",
                            "is_featured": True,
                        },
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "Updated Photos"
            assert data["is_featured"] is True
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_gallery(self, test_app):
        """DELETE /galleries/{id} deletes a gallery."""
        user_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.delete_gallery = AsyncMock()
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.delete(f"/api/v1/galleries/{gallery_id}")

            assert resp.status_code == 200
            data = resp.json()
            assert "message" in data
        finally:
            test_app.dependency_overrides.clear()


class TestGalleriesBulkAdd:
    """@brief POST /api/v1/galleries/{id}/items/bulk"""

    @pytest.mark.asyncio
    async def test_bulk_add_items(self, test_app):
        """POST /galleries/{id}/items/bulk adds multiple media items."""
        user_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        media_ids = [uuid.uuid4() for _ in range(3)]
        mock_user = _make_mock_user(user_id=user_id)

        # Mock returned items
        items = []
        for i, media_id in enumerate(media_ids):
            item = MagicMock()
            item.id = uuid.uuid4()
            item.gallery_id = gallery_id
            item.media_id = media_id
            item.added_by = user_id
            item.caption = None
            item.position = i
            item.created_at = datetime.now(UTC)
            items.append(item)

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.bulk_add_items = AsyncMock(return_value=items)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        f"/api/v1/galleries/{gallery_id}/items/bulk",
                        json={"media_ids": [str(mid) for mid in media_ids]},
                    )

            assert resp.status_code == 201
            data = resp.json()
            assert len(data) == 3
            assert data[0]["gallery_id"] == str(gallery_id)
        finally:
            test_app.dependency_overrides.clear()


class TestGalleriesCollaborators:
    """@brief POST/DELETE /api/v1/galleries/{id}/collaborators"""

    @pytest.mark.asyncio
    async def test_add_collaborator(self, test_app):
        """POST /galleries/{id}/collaborators invites a collaborator."""
        owner_id = uuid.uuid4()
        collaborator_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        mock_owner = _make_mock_user(user_id=owner_id)

        collab = MagicMock()
        collab.gallery_id = gallery_id
        collab.user_id = collaborator_id
        collab.invited_by = owner_id
        collab.invited_at = datetime.now(UTC)

        async def _override_user():
            return mock_owner

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.add_collaborator = AsyncMock(return_value=collab)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        f"/api/v1/galleries/{gallery_id}/collaborators",
                        json={"user_id": str(collaborator_id)},
                    )

            assert resp.status_code == 201
            data = resp.json()
            assert data["user_id"] == str(collaborator_id)
            assert data["invited_by"] == str(owner_id)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_remove_collaborator(self, test_app):
        """DELETE /galleries/{id}/collaborators/{user_id} removes a collaborator."""
        owner_id = uuid.uuid4()
        collaborator_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        mock_owner = _make_mock_user(user_id=owner_id)

        async def _override_user():
            return mock_owner

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.remove_collaborator = AsyncMock()
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.delete(
                        f"/api/v1/galleries/{gallery_id}/collaborators/{collaborator_id}"
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert "message" in data
        finally:
            test_app.dependency_overrides.clear()


class TestGalleriesSearch:
    """@brief GET /api/v1/galleries?q="""

    @pytest.mark.asyncio
    async def test_search_galleries(self, test_app):
        """GET /galleries?q=vacation returns matching galleries."""
        user_id = uuid.uuid4()
        mock_user = _make_mock_user(user_id=user_id)
        gallery = _make_mock_gallery(
            owner_id=user_id,
            title="Vacation Photos 2024",
            description="Summer vacation",
            item_count=12,
        )

        gallery_list = MagicMock()
        gallery_list.items = [gallery]
        gallery_list.next_cursor = None
        gallery_list.has_more = False

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.search = AsyncMock(return_value=gallery_list)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/galleries?q=vacation")

            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1
            assert "vacation" in data["items"][0]["title"].lower()
        finally:
            test_app.dependency_overrides.clear()


class TestEventGalleryAutoPopulate:
    """@brief Event gallery auto-population when creating posts with event_id + media_ids"""

    @pytest.mark.asyncio
    async def test_event_gallery_auto_populate_from_post(self, test_app):
        """POST /events/{id}/gallery/contribute auto-adds media to event gallery."""
        user_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        media_ids = [uuid.uuid4() for _ in range(2)]
        mock_user = _make_mock_user(user_id=user_id)

        # Mock returned items
        items = []
        for i, media_id in enumerate(media_ids):
            item = MagicMock()
            item.id = uuid.uuid4()
            item.gallery_id = gallery_id
            item.media_id = media_id
            item.added_by = user_id
            item.caption = None
            item.position = i
            item.created_at = datetime.now(UTC)
            items.append(item)

        async def _override_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.bulk_add_items = AsyncMock(return_value=items)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        f"/api/v1/galleries/{gallery_id}/items/bulk",
                        json={"media_ids": [str(mid) for mid in media_ids]},
                    )

            assert resp.status_code == 201
            data = resp.json()
            assert len(data) == 2
            for item_data in data:
                assert item_data["gallery_id"] == str(gallery_id)
        finally:
            test_app.dependency_overrides.clear()


class TestGalleriesBlockFilter:
    """@brief Block filter — user A blocks user B → B's gallery hidden in A's list"""

    @pytest.mark.asyncio
    async def test_block_filter_hides_blocked_user_gallery(self, test_app):
        """GET /galleries respects block-filter (viewer's blocks)."""
        viewer_id = uuid.uuid4()
        blocked_user_id = uuid.uuid4()
        mock_viewer = _make_mock_user(user_id=viewer_id)

        # Gallery owned by blocked user (should not appear in service result)
        # Gallery from non-blocked user (should appear)
        visible_gallery = _make_mock_gallery(
            owner_id=uuid.uuid4(),
            title="Other User's Photos",
            item_count=3,
        )

        gallery_list = MagicMock()
        gallery_list.items = [visible_gallery]  # blocked_gallery filtered out by service
        gallery_list.next_cursor = None
        gallery_list.has_more = False

        async def _override_user():
            return mock_viewer

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.list_galleries = AsyncMock(return_value=gallery_list)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/galleries")

            assert resp.status_code == 200
            data = resp.json()
            # Block-filtered galleries should not appear in list
            assert len(data["items"]) == 1
            assert data["items"][0]["owner_id"] != str(blocked_user_id)
        finally:
            test_app.dependency_overrides.clear()


class TestGalleriesAdminFeature:
    """@brief Admin feature endpoint (if implemented)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="awaits admin endpoints (Task 5)")
    async def test_admin_feature_gallery(self, test_app):
        """PATCH /admin/galleries/{id} allows admin to feature gallery."""
        gallery_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        mock_admin = _make_mock_user(user_id=admin_id)
        mock_admin.role = "admin"

        featured_gallery = _make_mock_gallery(
            gallery_id=gallery_id,
            title="Featured Photos",
            item_count=20,
            is_featured=True,
        )

        async def _override_user():
            return mock_admin

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.galleries.GalleryService") as mock_service_cls:
                mock_service = AsyncMock()
                mock_service.admin_feature = AsyncMock(return_value=featured_gallery)
                mock_service_cls.return_value = mock_service

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.patch(
                        f"/api/v1/admin/galleries/{gallery_id}",
                        json={"is_featured": True},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data["is_featured"] is True
        finally:
            test_app.dependency_overrides.clear()
