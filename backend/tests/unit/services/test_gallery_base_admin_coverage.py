"""
@file test_gallery_base_admin_coverage.py
@brief Branch-coverage tests for gallery_base and gallery_admin.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.services.gallery_service import GalleryService
from tests.unit.services._gallery_fixtures import (  # noqa: F401
    _gallery,
    repo,
    service,
    session,
)

class TestBaseVisibility:
    async def test_subgroup_without_id_is_hidden(self, service: GalleryService) -> None:
        g = _gallery(visibility="subgroup", subgroup_id=None)
        assert await service._can_view(g, uuid.uuid4()) is False

    async def test_subgroup_member_can_view(
        self, service: GalleryService, session: AsyncMock
    ) -> None:
        sg = uuid.uuid4()
        g = _gallery(visibility="subgroup", subgroup_id=sg)
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sg])))
        )
        with patch(
            "app.repositories.subgroup_repo.expand_with_descendants",
            new=AsyncMock(return_value=[sg]),
        ):
            assert await service._can_view(g, uuid.uuid4()) is True

    async def test_subgroup_non_member_cannot_view(
        self, service: GalleryService, session: AsyncMock
    ) -> None:
        g = _gallery(visibility="subgroup", subgroup_id=uuid.uuid4())
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
        with patch(
            "app.repositories.subgroup_repo.expand_with_descendants",
            new=AsyncMock(return_value=[]),
        ):
            assert await service._can_view(g, uuid.uuid4()) is False

    async def test_private_collaborator_can_view(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        repo.is_collaborator.return_value = True
        g = _gallery(visibility="private")
        assert await service._can_view(g, uuid.uuid4()) is True

    async def test_unknown_visibility_denied(self, service: GalleryService) -> None:
        assert await service._can_view(_gallery(visibility="weird"), uuid.uuid4()) is False


class TestBaseContribute:
    async def test_collaborators_policy_allows_collaborator(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        repo.is_collaborator.return_value = True
        g = _gallery(contribution_policy="collaborators")
        assert await service._can_contribute(g, uuid.uuid4()) is True

    async def test_community_policy_follows_view(self, service: GalleryService) -> None:
        g = _gallery(contribution_policy="community", visibility="community")
        assert await service._can_contribute(g, uuid.uuid4()) is True

    async def test_unknown_policy_denied(self, service: GalleryService) -> None:
        g = _gallery(contribution_policy="weird")
        assert await service._can_contribute(g, uuid.uuid4()) is False


class TestAdminNotFound:
    async def test_force_visibility_not_found(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.admin_force_visibility(uuid.uuid4(), "private", uuid.uuid4())

    async def test_delete_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.admin_delete(uuid.uuid4(), uuid.uuid4())


