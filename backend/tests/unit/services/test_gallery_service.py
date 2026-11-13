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
from app.repositories.audit_repo import AuditRepository
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
def audit_repo() -> AsyncMock:
    return AsyncMock(spec=AuditRepository)


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
def service(repo: AsyncMock, session: AsyncMock, audit_repo: AsyncMock) -> GalleryService:
    svc = GalleryService(gallery_repo=repo, community_id=COMMUNITY_ID, session=session)
    svc._audit_repo = audit_repo
    return svc


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

    @pytest.mark.asyncio
    async def test_create_with_subgroup_id_persists(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        repo.create.side_effect = _fill
        user_id = uuid.uuid4()
        subgroup_id = uuid.uuid4()
        result = await service.create_gallery(
            user_id,
            GalleryCreate(
                title="Group Photos",
                visibility="subgroup",
                subgroup_id=subgroup_id,
            ),
        )
        assert result.subgroup_id == subgroup_id
        assert result.visibility == "subgroup"


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


class TestGetOrCreateForEvent:
    @pytest.mark.asyncio
    async def test_returns_existing_gallery(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        """get_or_create_for_event returns existing gallery if one exists."""
        event_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        existing_gallery = _make_gallery(event_id=event_id, visibility="community")

        # Mock the repo to return an existing gallery
        repo.get_event_gallery.return_value = existing_gallery

        # Mock event_service to verify event is accessible
        from app.models.event import Event

        mock_event = MagicMock(spec=Event)
        mock_event.id = event_id
        mock_event.title = "Summer Picnic"
        mock_event.visibility = "community"
        mock_event.subgroup_id = None
        mock_event.author_id = uuid.uuid4()

        repo.get_by_id = AsyncMock()
        # We'll need to mock the event fetch

        result = await service.get_or_create_for_event(event_id, viewer_id=viewer_id)
        assert result.id == existing_gallery.id
        assert result.event_id == event_id
        repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_new_gallery_when_absent(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        """get_or_create_for_event creates new gallery with event settings."""
        event_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        event_author_id = uuid.uuid4()
        subgroup_id = uuid.uuid4()

        # Mock: no existing gallery
        repo.get_event_gallery.return_value = None

        # Mock event
        from app.models.event import Event

        mock_event = MagicMock(spec=Event)
        mock_event.id = event_id
        mock_event.title = "Summer Picnic"
        mock_event.visibility = "subgroup"
        mock_event.subgroup_id = subgroup_id
        mock_event.author_id = event_author_id

        session.get = AsyncMock(return_value=mock_event)
        repo.get_by_id = AsyncMock(return_value=mock_event)
        repo.create.side_effect = _fill

        # Mock _user_subgroup_ids to include subgroup_id so viewer can see the event
        service._user_subgroup_ids = AsyncMock(return_value=[subgroup_id])

        result = await service.get_or_create_for_event(event_id, viewer_id=viewer_id)

        # Verify the created gallery has event's properties
        assert result.title == "Summer Picnic"
        assert result.visibility == "subgroup"
        assert result.subgroup_id == subgroup_id
        assert result.event_id == event_id
        assert result.owner_id == event_author_id
        repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_when_event_missing(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        """get_or_create_for_event raises NotFoundError if event not found."""
        event_id = uuid.uuid4()
        viewer_id = uuid.uuid4()

        # Mock: no existing gallery
        repo.get_event_gallery.return_value = None

        # Mock: event not found
        session.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_or_create_for_event(event_id, viewer_id=viewer_id)


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


class TestAutoAddToEventGallery:
    @pytest.mark.asyncio
    async def test_auto_add_to_event_gallery(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        """auto_add_to_event_gallery() adds media to event gallery."""
        post_id = uuid.uuid4()
        event_id = uuid.uuid4()
        gallery = _make_gallery(event_id=event_id, is_event_gallery=True)
        repo.get_event_gallery.return_value = gallery
        repo.get_item.return_value = None

        def _fill_item(i: GalleryItem) -> GalleryItem:
            i.id = uuid.uuid4()
            i.created_at = datetime.now(UTC)
            return i

        repo.add_item.side_effect = _fill_item

        media_ids = [uuid.uuid4(), uuid.uuid4()]
        result = await service.auto_add_to_event_gallery(post_id, event_id, media_ids)
        assert len(result) == 2
        assert repo.add_item.call_count == 2

    @pytest.mark.asyncio
    async def test_auto_add_to_event_gallery_empty_media(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        """auto_add_to_event_gallery() with empty media_ids returns None."""
        post_id = uuid.uuid4()
        event_id = uuid.uuid4()
        result = await service.auto_add_to_event_gallery(post_id, event_id, [])
        repo.get_event_gallery.assert_not_awaited()
        assert result is None


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_filters_by_visibility(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        viewer = uuid.uuid4()
        public_gallery = _make_gallery(visibility="community")
        private_gallery_owned_by_other = _make_gallery(visibility="private")
        repo.search.return_value = [public_gallery, private_gallery_owned_by_other]
        repo.is_collaborator.return_value = False

        results = await service.search(q="vacation", viewer_id=viewer)
        result_ids = [r.id for r in results.items]
        assert public_gallery.id in result_ids
        assert private_gallery_owned_by_other.id not in result_ids


class TestFeaturedAndSort:
    @pytest.mark.asyncio
    async def test_list_galleries_with_featured_and_sort(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        """Test that featured filter and sort parameters are passed through repo."""
        viewer = uuid.uuid4()

        # Create featured galleries with different item counts for sorting
        g1 = _make_gallery(item_count=5)
        g1.is_featured = True
        g1.created_at = datetime.now(UTC)

        g2 = _make_gallery(item_count=10)
        g2.is_featured = True
        g2.created_at = datetime.now(UTC)

        # Mock return values - popular sort returns by item count DESC
        repo.list_visible.return_value = ([g2, g1], None)

        result = await service.list_galleries(viewer, featured_only=True, sort="popular")

        # Verify repo was called with correct params
        repo.list_visible.assert_awaited_once()
        call_kwargs = repo.list_visible.call_args[1]
        assert call_kwargs.get("featured_only") is True
        assert call_kwargs.get("sort") == "popular"

        # Verify results are returned in correct order (by item count DESC)
        assert len(result.items) == 2
        assert result.items[0].item_count == 10
        assert result.items[1].item_count == 5


class TestAdminModeration:
    @pytest.mark.asyncio
    async def test_admin_feature_writes_audit_log(
        self, service: GalleryService, repo: AsyncMock, audit_repo: AsyncMock
    ) -> None:
        """Admin can feature a gallery and audit log is written."""
        gallery = _make_gallery()
        gallery.is_featured = False
        admin_id = uuid.uuid4()
        repo.get_by_id.return_value = gallery

        def update_side_effect(g: Gallery, updates: dict) -> Gallery:
            for key, value in updates.items():
                setattr(g, key, value)
            return g

        repo.update.side_effect = update_side_effect

        result = await service.admin_feature(gallery.id, featured=True, admin_id=admin_id)

        repo.update.assert_awaited_once()
        audit_repo.append.assert_awaited_once()
        call_args = audit_repo.append.call_args
        assert call_args[1]["action"] == "admin.gallery.featured"
        assert call_args[1]["target_type"] == "gallery"
        assert call_args[1]["target_id"] == gallery.id
        assert call_args[1]["extra_data"]["featured"] is True
        assert result.is_featured is True

    @pytest.mark.asyncio
    async def test_admin_force_visibility_writes_audit_log(
        self, service: GalleryService, repo: AsyncMock, audit_repo: AsyncMock
    ) -> None:
        """Admin can force-change visibility and audit log is written."""
        gallery = _make_gallery(visibility="community")
        admin_id = uuid.uuid4()
        repo.get_by_id.return_value = gallery

        def update_side_effect(g: Gallery, updates: dict) -> Gallery:
            for key, value in updates.items():
                setattr(g, key, value)
            return g

        repo.update.side_effect = update_side_effect

        result = await service.admin_force_visibility(
            gallery.id, visibility="private", admin_id=admin_id
        )

        repo.update.assert_awaited_once()
        audit_repo.append.assert_awaited_once()
        call_args = audit_repo.append.call_args
        assert call_args[1]["action"] == "admin.gallery.visibility_changed"
        assert call_args[1]["target_type"] == "gallery"
        assert call_args[1]["target_id"] == gallery.id
        assert call_args[1]["extra_data"]["new_visibility"] == "private"
        assert call_args[1]["extra_data"]["old_visibility"] == "community"
        assert result.visibility == "private"

    @pytest.mark.asyncio
    async def test_admin_delete_writes_audit_log(
        self, service: GalleryService, repo: AsyncMock, audit_repo: AsyncMock
    ) -> None:
        """Admin can delete a gallery and audit log is written."""
        gallery = _make_gallery()
        admin_id = uuid.uuid4()
        repo.get_by_id.return_value = gallery

        def update_side_effect(g: Gallery, updates: dict) -> Gallery:
            for key, value in updates.items():
                setattr(g, key, value)
            return g

        repo.update.side_effect = update_side_effect

        await service.admin_delete(gallery.id, admin_id=admin_id)

        repo.update.assert_awaited_once()
        audit_repo.append.assert_awaited_once()
        call_args = audit_repo.append.call_args
        assert call_args[1]["action"] == "admin.gallery.deleted"
        assert call_args[1]["target_type"] == "gallery"
        assert call_args[1]["target_id"] == gallery.id

    @pytest.mark.asyncio
    async def test_admin_feature_gallery_not_found(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        """Admin feature raises NotFoundError if gallery not found."""
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.admin_feature(uuid.uuid4(), featured=True, admin_id=uuid.uuid4())


class TestActorName:
    """@brief _actor_name resolves display names for notification payloads."""

    async def test_returns_display_name(self, service: GalleryService, session: AsyncMock) -> None:
        user = MagicMock()
        user.display_name = "Alice"
        session.get.return_value = user
        assert await service._actor_name(uuid.uuid4()) == "Alice"

    async def test_falls_back_when_user_missing(
        self, service: GalleryService, session: AsyncMock
    ) -> None:
        session.get.return_value = None
        assert await service._actor_name(uuid.uuid4()) == "Someone"
