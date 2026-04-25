"""
@file test_gallery_service.py
@brief Unit tests for GalleryService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem
from app.repositories.gallery_repo import GalleryRepository
from app.schemas.gallery import (
    GalleryCreate,
    GalleryItemBulkCreate,
    GalleryItemCreate,
    GalleryUpdate,
)
from app.services.gallery_service import GalleryService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_gallery(
    *,
    owner_id: uuid.UUID | None = None,
    visibility: str = "community",
    contribution_policy: str = "owner_only",
    subgroup_id: uuid.UUID | None = None,
    is_default: bool = False,
    is_event_gallery: bool = False,
    event_id: uuid.UUID | None = None,
    item_count: int = 0,
) -> MagicMock:
    g = MagicMock(spec=Gallery)
    g.id = uuid.uuid4()
    g.community_id = COMMUNITY_ID
    g.owner_id = owner_id or uuid.uuid4()
    g.title = "Test Gallery"
    g.description = "desc"
    g.cover_media_id = None
    g.event_id = event_id
    g.subgroup_id = subgroup_id
    g.visibility = visibility
    g.contribution_policy = contribution_policy
    g.item_count = item_count
    g.is_featured = False
    g.is_default = is_default
    g.is_event_gallery = is_event_gallery
    g.created_at = datetime.now(UTC)
    g.updated_at = datetime.now(UTC)
    return g


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=GalleryRepository)
    r.is_collaborator.return_value = False
    r.list_collaborators.return_value = []
    return r


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock()
    exec_result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    exec_result.scalars.return_value = scalars
    s.execute.return_value = exec_result
    return s


@pytest.fixture
def service(repo: AsyncMock, session: AsyncMock) -> GalleryService:
    return GalleryService(gallery_repo=repo, community_id=COMMUNITY_ID, session=session)


def _fill(g: Gallery) -> Gallery:
    g.id = uuid.uuid4()
    g.created_at = datetime.now(UTC)
    g.updated_at = datetime.now(UTC)
    g.item_count = 0
    g.is_featured = False
    g.is_default = getattr(g, "is_default", False) or False
    g.is_event_gallery = getattr(g, "is_event_gallery", False) or False
    return g


class TestCreateGallery:
    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.create.side_effect = _fill
        user_id = uuid.uuid4()
        result = await service.create_gallery(user_id, GalleryCreate(title="Vacation 2026"))
        assert result.title == "Vacation 2026"
        assert result.owner_id == user_id

    @pytest.mark.asyncio
    async def test_subgroup_visibility_requires_subgroup(self, service: GalleryService) -> None:
        with pytest.raises(AppError, match="[Ss]ubgroup"):
            await service.create_gallery(
                uuid.uuid4(),
                GalleryCreate(title="X", visibility="subgroup"),
            )


class TestDefaultGallery:
    @pytest.mark.asyncio
    async def test_default_auto_created(self, service: GalleryService, repo: AsyncMock) -> None:
        user_id = uuid.uuid4()
        repo.get_default_for_user.return_value = None
        repo.create.side_effect = _fill

        result = await service.ensure_default_gallery(user_id)
        assert result.owner_id == user_id

    @pytest.mark.asyncio
    async def test_default_idempotent(self, service: GalleryService, repo: AsyncMock) -> None:
        user_id = uuid.uuid4()
        existing = _make_gallery(owner_id=user_id, is_default=True)
        repo.get_default_for_user.return_value = existing

        result = await service.ensure_default_gallery(user_id)
        assert result.id == existing.id
        repo.create.assert_not_awaited()


class TestEventGallery:
    @pytest.mark.asyncio
    async def test_event_gallery_auto_created(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        event_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        repo.get_event_gallery.return_value = None
        repo.create.side_effect = _fill

        result = await service.ensure_event_gallery(event_id, owner_id, "Picnic")
        assert result.event_id == event_id
        assert result.title == "Picnic"


class TestContributionPolicy:
    @pytest.mark.asyncio
    async def test_owner_only_rejects_non_owner(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        gallery = _make_gallery(contribution_policy="owner_only")
        repo.get_by_id.return_value = gallery
        with pytest.raises(AuthorizationError):
            await service.add_item(
                gallery.id, uuid.uuid4(), GalleryItemCreate(media_id=uuid.uuid4())
            )

    @pytest.mark.asyncio
    async def test_collaborators_rejects_non_collab(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        gallery = _make_gallery(contribution_policy="collaborators")
        repo.get_by_id.return_value = gallery
        repo.is_collaborator.return_value = False

        with pytest.raises(AuthorizationError):
            await service.add_item(
                gallery.id, uuid.uuid4(), GalleryItemCreate(media_id=uuid.uuid4())
            )

    @pytest.mark.asyncio
    async def test_collaborator_can_add(self, service: GalleryService, repo: AsyncMock) -> None:
        gallery = _make_gallery(contribution_policy="collaborators")
        repo.get_by_id.return_value = gallery
        repo.is_collaborator.return_value = True
        repo.get_item.return_value = None

        def _fill_item(i: GalleryItem) -> GalleryItem:
            i.id = uuid.uuid4()
            i.created_at = datetime.now(UTC)
            return i

        repo.add_item.side_effect = _fill_item

        result = await service.add_item(
            gallery.id, uuid.uuid4(), GalleryItemCreate(media_id=uuid.uuid4())
        )
        assert result.gallery_id == gallery.id

    @pytest.mark.asyncio
    async def test_owner_can_always_add(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        gallery = _make_gallery(owner_id=owner, contribution_policy="owner_only")
        repo.get_by_id.return_value = gallery
        repo.get_item.return_value = None

        def _fill_item(i: GalleryItem) -> GalleryItem:
            i.id = uuid.uuid4()
            i.created_at = datetime.now(UTC)
            return i

        repo.add_item.side_effect = _fill_item

        result = await service.add_item(gallery.id, owner, GalleryItemCreate(media_id=uuid.uuid4()))
        assert result.added_by == owner


class TestVisibility:
    @pytest.mark.asyncio
    async def test_private_hidden_from_others(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        gallery = _make_gallery(visibility="private")
        repo.get_by_id.return_value = gallery
        with pytest.raises(AuthorizationError):
            await service.get_gallery(gallery.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_private_visible_to_owner(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        gallery = _make_gallery(owner_id=owner, visibility="private")
        repo.get_by_id.return_value = gallery
        result = await service.get_gallery(gallery.id, owner)
        assert result.id == gallery.id


class TestUpdateDelete:
    @pytest.mark.asyncio
    async def test_only_owner_can_update(self, service: GalleryService, repo: AsyncMock) -> None:
        gallery = _make_gallery()
        repo.get_by_id.return_value = gallery
        with pytest.raises(AuthorizationError):
            await service.update_gallery(gallery.id, uuid.uuid4(), GalleryUpdate(title="Hijacked"))

    @pytest.mark.asyncio
    async def test_not_found_raises(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.delete_gallery(uuid.uuid4(), uuid.uuid4())


class TestCollaborators:
    @pytest.mark.asyncio
    async def test_only_owner_invites(self, service: GalleryService, repo: AsyncMock) -> None:
        gallery = _make_gallery()
        repo.get_by_id.return_value = gallery
        with pytest.raises(AuthorizationError):
            await service.add_collaborator(gallery.id, uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_invite_creates_collab(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        gallery = _make_gallery(owner_id=owner)
        repo.get_by_id.return_value = gallery
        repo.is_collaborator.return_value = False
        invitee = uuid.uuid4()

        collab = MagicMock(spec=GalleryCollaborator)
        collab.gallery_id = gallery.id
        collab.user_id = invitee
        collab.invited_by = owner
        collab.invited_at = datetime.now(UTC)
        repo.add_collaborator.return_value = collab

        result = await service.add_collaborator(gallery.id, owner, invitee)
        assert result.user_id == invitee


class TestBulkAdd:
    @pytest.mark.asyncio
    async def test_bulk_add_items(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        gallery = _make_gallery(owner_id=owner)
        repo.get_by_id.return_value = gallery
        repo.get_item.return_value = None

        def _fill_item(i: GalleryItem) -> GalleryItem:
            i.id = uuid.uuid4()
            i.created_at = datetime.now(UTC)
            return i

        repo.add_item.side_effect = _fill_item

        ids = [uuid.uuid4() for _ in range(3)]
        result = await service.bulk_add_items(
            gallery.id, owner, GalleryItemBulkCreate(media_ids=ids)
        )
        assert len(result) == 3
