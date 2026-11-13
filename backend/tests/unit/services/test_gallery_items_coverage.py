"""
@file test_gallery_items_coverage.py
@brief Branch-coverage tests for gallery_items.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.gallery import GalleryCollaborator
from app.models.user import User
from app.schemas.gallery import (
    GalleryItemBulkCreate,
    GalleryItemCreate,
    GalleryItemUpdate,
)
from app.services.gallery_service import GalleryService
from tests.unit.services._gallery_fixtures import (  # noqa: F401
    _gallery,
    _item,
    repo,
    service,
    session,
)

class TestEnsureGalleries:
    async def test_default_returns_existing(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_default_for_user.return_value = _gallery()
        await service.ensure_default_gallery(uuid.uuid4())
        repo.create.assert_not_awaited()

    async def test_default_creates(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_default_for_user.return_value = None
        res = await service.ensure_default_gallery(uuid.uuid4())
        assert res.is_default is True

    async def test_event_returns_existing(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_event_gallery.return_value = _gallery()
        await service.ensure_event_gallery(uuid.uuid4(), uuid.uuid4(), "t")
        repo.create.assert_not_awaited()

    async def test_event_creates(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_event_gallery.return_value = None
        res = await service.ensure_event_gallery(uuid.uuid4(), uuid.uuid4(), "t")
        assert res.is_event_gallery is True


class TestListItems:
    async def test_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.list_items(uuid.uuid4(), uuid.uuid4())

    async def test_forbidden(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery(visibility="private")
        with pytest.raises(AuthorizationError):
            await service.list_items(uuid.uuid4(), uuid.uuid4())

    async def test_returns_items(self, service: GalleryService, repo: AsyncMock) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        repo.list_items.return_value = ([_item(g.id)], None)
        assert len(await service.list_items(g.id, uuid.uuid4())) == 1


class TestAddItem:
    async def test_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.add_item(
                uuid.uuid4(), uuid.uuid4(), GalleryItemCreate(media_id=uuid.uuid4())
            )

    async def test_forbidden(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery()
        with pytest.raises(AuthorizationError):
            await service.add_item(
                uuid.uuid4(), uuid.uuid4(), GalleryItemCreate(media_id=uuid.uuid4())
            )

    async def test_existing_returned(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        repo.get_item.return_value = _item(g.id)
        await service.add_item(g.id, owner, GalleryItemCreate(media_id=uuid.uuid4()))
        repo.add_item.assert_not_awaited()

    async def test_creates_with_default_position(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        owner = uuid.uuid4()
        g = _gallery(owner_id=owner, item_count=4)
        repo.get_by_id.return_value = g
        repo.get_item.return_value = None
        res = await service.add_item(g.id, owner, GalleryItemCreate(media_id=uuid.uuid4()))
        assert res.position == 4


class TestBulkAddBranches:
    async def test_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.bulk_add_items(
                uuid.uuid4(), uuid.uuid4(), GalleryItemBulkCreate(media_ids=[uuid.uuid4()])
            )

    async def test_forbidden(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery()
        with pytest.raises(AuthorizationError):
            await service.bulk_add_items(
                uuid.uuid4(), uuid.uuid4(), GalleryItemBulkCreate(media_ids=[uuid.uuid4()])
            )

    async def test_skips_existing(self, service: GalleryService, repo: AsyncMock) -> None:
        owner = uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        repo.get_item.return_value = _item(g.id)
        res = await service.bulk_add_items(
            g.id, owner, GalleryItemBulkCreate(media_ids=[uuid.uuid4()])
        )
        assert len(res) == 1
        repo.add_item.assert_not_awaited()


class TestUpdateRemoveItem:
    async def test_update_gallery_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.update_item(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), GalleryItemUpdate(caption="x")
            )

    async def test_update_item_missing(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        repo.get_by_id.return_value = _gallery()
        session.get.return_value = None
        with pytest.raises(NotFoundError):
            await service.update_item(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), GalleryItemUpdate(caption="x")
            )

    async def test_update_item_wrong_gallery(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        session.get.return_value = _item(uuid.uuid4())
        with pytest.raises(NotFoundError):
            await service.update_item(g.id, uuid.uuid4(), uuid.uuid4(), GalleryItemUpdate())

    async def test_update_forbidden(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        session.get.return_value = _item(g.id)
        with pytest.raises(AuthorizationError):
            await service.update_item(g.id, uuid.uuid4(), uuid.uuid4(), GalleryItemUpdate())

    async def test_update_ok(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        owner = uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        item = _item(g.id)
        session.get.return_value = item
        repo.update_item.return_value = item
        await service.update_item(g.id, item.id, owner, GalleryItemUpdate(caption="c"))
        repo.update_item.assert_awaited_once_with(item, {"caption": "c"})

    async def test_remove_gallery_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.remove_item(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_remove_item_missing(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        repo.get_by_id.return_value = _gallery()
        session.get.return_value = None
        with pytest.raises(NotFoundError):
            await service.remove_item(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_remove_forbidden(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        session.get.return_value = _item(g.id)
        with pytest.raises(AuthorizationError):
            await service.remove_item(g.id, uuid.uuid4(), uuid.uuid4())

    async def test_remove_by_adder(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        user = uuid.uuid4()
        item = _item(g.id, added_by=user)
        session.get.return_value = item
        await service.remove_item(g.id, item.id, user)
        repo.remove_item.assert_awaited_once_with(item)


class TestCollaboratorBranches:
    async def test_list_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.list_collaborators(uuid.uuid4(), uuid.uuid4())

    async def test_list_forbidden(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery(visibility="private")
        with pytest.raises(AuthorizationError):
            await service.list_collaborators(uuid.uuid4(), uuid.uuid4())

    async def test_list_ok(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery()
        c = MagicMock(spec=GalleryCollaborator)
        c.gallery_id, c.user_id = uuid.uuid4(), uuid.uuid4()
        c.invited_by, c.invited_at = None, datetime.now(UTC)
        repo.list_collaborators.return_value = [c]
        assert len(await service.list_collaborators(uuid.uuid4(), uuid.uuid4())) == 1

    async def test_actor_name_known_and_unknown(
        self, service: GalleryService, session: AsyncMock
    ) -> None:
        user = MagicMock(spec=User)
        user.display_name = "Ann"
        session.get.return_value = user
        assert await service._actor_name(uuid.uuid4()) == "Ann"
        session.get.return_value = None
        assert await service._actor_name(uuid.uuid4()) == "Someone"

    async def test_add_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.add_collaborator(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_add_existing_collaborator_returned(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        owner, invitee = uuid.uuid4(), uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        repo.is_collaborator.return_value = True
        c = MagicMock(spec=GalleryCollaborator)
        c.gallery_id, c.user_id = g.id, invitee
        c.invited_by, c.invited_at = owner, datetime.now(UTC)
        repo.list_collaborators.return_value = [c]
        res = await service.add_collaborator(g.id, owner, invitee)
        assert res.user_id == invitee
        repo.add_collaborator.assert_not_awaited()

    async def test_add_notifies(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        owner, invitee = uuid.uuid4(), uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        c = MagicMock(spec=GalleryCollaborator)
        c.gallery_id, c.user_id = g.id, invitee
        c.invited_by, c.invited_at = owner, datetime.now(UTC)
        repo.add_collaborator.return_value = c
        session.get.return_value = None
        notif = AsyncMock()
        service._notifications = notif
        await service.add_collaborator(g.id, owner, invitee)
        notif.notify.assert_awaited_once()
        assert notif.notify.await_args.kwargs["type"] == "gallery_activity"

    async def test_add_notify_failure_swallowed(
        self, service: GalleryService, repo: AsyncMock, session: AsyncMock
    ) -> None:
        owner, invitee = uuid.uuid4(), uuid.uuid4()
        g = _gallery(owner_id=owner)
        repo.get_by_id.return_value = g
        c = MagicMock(spec=GalleryCollaborator)
        c.gallery_id, c.user_id = g.id, invitee
        c.invited_by, c.invited_at = owner, datetime.now(UTC)
        repo.add_collaborator.return_value = c
        session.get.return_value = None
        service._notifications = AsyncMock(notify=AsyncMock(side_effect=RuntimeError("x")))
        res = await service.add_collaborator(g.id, owner, invitee)
        assert res.user_id == invitee

    async def test_remove_not_found(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.remove_collaborator(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_remove_forbidden(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_by_id.return_value = _gallery()
        with pytest.raises(AuthorizationError):
            await service.remove_collaborator(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    async def test_remove_self_allowed(self, service: GalleryService, repo: AsyncMock) -> None:
        g = _gallery()
        repo.get_by_id.return_value = g
        me = uuid.uuid4()
        await service.remove_collaborator(g.id, me, me)
        repo.remove_collaborator.assert_awaited_once_with(g.id, me)


class TestAutoAdd:
    async def test_event_gallery_missing(self, service: GalleryService, repo: AsyncMock) -> None:
        repo.get_event_gallery.return_value = None
        assert (
            await service.auto_add_to_event_gallery(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()])
            is None
        )

    async def test_event_gallery_skips_existing(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_event_gallery.return_value = g
        repo.get_item.return_value = _item(g.id)
        res = await service.auto_add_to_event_gallery(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()])
        assert res is not None and len(res) == 1
        repo.add_item.assert_not_awaited()

    async def test_default_existing_item(self, service: GalleryService, repo: AsyncMock) -> None:
        g = _gallery()
        repo.get_default_for_user.return_value = g
        repo.get_item.return_value = _item(g.id)
        assert await service.auto_add_to_default(uuid.uuid4(), uuid.uuid4()) is not None
        repo.add_item.assert_not_awaited()

    async def test_default_adds_item(self, service: GalleryService, repo: AsyncMock) -> None:
        g = _gallery(item_count=2)
        repo.get_default_for_user.return_value = g
        repo.get_item.return_value = None
        res = await service.auto_add_to_default(uuid.uuid4(), uuid.uuid4())
        assert res is not None and res.position == 2

    async def test_default_created_then_loaded(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        g = _gallery()
        repo.get_default_for_user.side_effect = [None, None]
        repo.get_by_id.return_value = g
        repo.get_item.return_value = None
        assert await service.auto_add_to_default(uuid.uuid4(), uuid.uuid4()) is not None
        repo.create.assert_awaited_once()

    async def test_default_unresolvable_returns_none(
        self, service: GalleryService, repo: AsyncMock
    ) -> None:
        repo.get_default_for_user.return_value = None
        repo.get_by_id.return_value = None
        assert await service.auto_add_to_default(uuid.uuid4(), uuid.uuid4()) is None
