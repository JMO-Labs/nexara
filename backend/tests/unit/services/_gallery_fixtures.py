"""
@file _gallery_fixtures.py
@brief Shared helpers and fixtures for gallery coverage tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.gallery import Gallery, GalleryItem
from app.repositories.gallery_repo import GalleryRepository
from app.services.gallery_service import GalleryService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _gallery(**kw: object) -> MagicMock:
    g = MagicMock(spec=Gallery)
    g.id = uuid.uuid4()
    g.community_id = COMMUNITY_ID
    g.owner_id = kw.get("owner_id") or uuid.uuid4()
    g.title = "G"
    g.description = None
    g.cover_media_id = None
    g.event_id = None
    g.subgroup_id = kw.get("subgroup_id")
    g.visibility = kw.get("visibility", "community")
    g.contribution_policy = kw.get("contribution_policy", "owner_only")
    g.item_count = kw.get("item_count", 0)
    g.is_featured = False
    g.is_default = False
    g.is_event_gallery = False
    g.created_at = datetime.now(UTC)
    g.updated_at = datetime.now(UTC)
    return g


def _item(gallery_id: uuid.UUID, added_by: uuid.UUID | None = None) -> MagicMock:
    i = MagicMock(spec=GalleryItem)
    i.id = uuid.uuid4()
    i.gallery_id = gallery_id
    i.media_id = uuid.uuid4()
    i.added_by = added_by or uuid.uuid4()
    i.caption = None
    i.position = 0
    i.created_at = datetime.now(UTC)
    return i


def _fill_item(i: GalleryItem) -> GalleryItem:
    i.id = uuid.uuid4()
    i.created_at = datetime.now(UTC)
    return i


def _fill_gallery(g: Gallery) -> Gallery:
    g.id = uuid.uuid4()
    g.created_at = datetime.now(UTC)
    g.updated_at = datetime.now(UTC)
    g.item_count = 0
    g.is_featured = False
    g.is_default = bool(g.is_default)
    g.is_event_gallery = bool(g.is_event_gallery)
    return g


@pytest.fixture
def repo() -> AsyncMock:
    r = AsyncMock(spec=GalleryRepository)
    r.is_collaborator.return_value = False
    r.list_collaborators.return_value = []
    r.add_item.side_effect = _fill_item
    r.create.side_effect = _fill_gallery
    return r


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repo: AsyncMock, session: AsyncMock) -> GalleryService:
    return GalleryService(gallery_repo=repo, community_id=COMMUNITY_ID, session=session)
