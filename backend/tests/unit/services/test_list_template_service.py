"""
@file test_list_template_service.py
@brief Unit tests for ListTemplateService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.list_template import ListTemplate, ListTemplateField, ListTemplateItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_template_repo import ListTemplateRepository
from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry
from app.services.list_template_service import ListTemplateService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR = uuid.uuid4()
OTHER = uuid.uuid4()


def _tpl() -> MagicMock:
    t = MagicMock(spec=ListTemplate)
    t.id = uuid.uuid4()
    t.community_id = CID
    t.author_id = AUTHOR
    t.deleted_at = None
    t.name = "Packing"
    t.description = "d"
    f = MagicMock(spec=ListTemplateField)
    f.key, f.label, f.type_key, f.required = "k", "K", "select", True
    f.config, f.position = {"options": []}, 0
    i = MagicMock(spec=ListTemplateItem)
    i.values, i.position = {"k": "a"}, 0
    t.fields, t.items = [f], [i]
    return t


@pytest.fixture
def parts():
    repo = AsyncMock(spec=ListTemplateRepository)
    registry = MagicMock(spec=ListFieldRegistry)
    registry.validate_config.side_effect = lambda k, c: c
    lists = AsyncMock(spec=ListRepository)
    lists.create.side_effect = lambda e: e
    items = AsyncMock(spec=ListItemRepository)
    svc = ListTemplateService(repo, registry, list_repo=lists, item_repo=items)
    return svc, repo, registry, lists, items


FIELD = {"key": "k", "label": "K", "type_key": "select", "config": {"options": [{"value": "a", "label": "A"}]}}


async def test_create_validates_fields(parts):
    svc, repo, registry, *_ = parts
    repo.create.side_effect = lambda e: e
    out = await svc.create(CID, AUTHOR, {"name": "T", "fields": [FIELD], "items": [{"values": {"k": "a"}}]})
    registry.validate_config.assert_called_once_with("select", FIELD["config"])
    assert out.name == "T"
    assert len(out.fields) == 1 and len(out.items) == 1


@pytest.mark.parametrize("exc", [ValueError("bad"), FieldTypeNotFound("x")])
async def test_create_invalid_config_raises_app_error(parts, exc):
    svc, repo, registry, *_ = parts
    registry.validate_config.side_effect = exc
    with pytest.raises(AppError):
        await svc.create(CID, AUTHOR, {"name": "T", "fields": [FIELD]})
    repo.create.assert_not_called()


async def test_list_for_community_delegates(parts):
    svc, repo, *_ = parts
    repo.list_for_community.return_value = ([], None)
    assert await svc.list_for_community(CID, AUTHOR, cursor="c", limit=5) == ([], None)
    repo.list_for_community.assert_awaited_once_with(CID, AUTHOR, cursor="c", limit=5)


async def test_get_by_id_missing(parts):
    svc, repo, *_ = parts
    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await svc.get_by_id(CID, uuid.uuid4(), AUTHOR)


async def test_get_by_id_hides_private_of_others(parts):
    svc, repo, *_ = parts
    t = _tpl()
    t.is_shared, t.is_system = False, False
    repo.get_by_id.return_value = t
    with pytest.raises(NotFoundError):
        await svc.get_by_id(CID, t.id, OTHER)
    assert await svc.get_by_id(CID, t.id, AUTHOR) is t


async def test_update_author_only(parts):
    svc, repo, *_ = parts
    t = _tpl()
    repo.get_by_id.return_value = t
    with pytest.raises(AuthorizationError):
        await svc.update(CID, t.id, OTHER, {"name": "x"})
    repo.update.assert_not_called()


async def test_update_validates_new_fields(parts):
    svc, repo, registry, *_ = parts
    t = _tpl()
    repo.get_by_id.return_value = t
    repo.update.side_effect = lambda e, d: e
    registry.validate_config.side_effect = ValueError("bad")
    with pytest.raises(AppError):
        await svc.update(CID, t.id, AUTHOR, {"fields": [FIELD]})
    registry.validate_config.side_effect = lambda k, c: c
    await svc.update(CID, t.id, AUTHOR, {"name": "n", "fields": [FIELD]})
    repo.update.assert_awaited_once()


async def test_delete_author_only(parts):
    svc, repo, *_ = parts
    t = _tpl()
    repo.get_by_id.return_value = t
    with pytest.raises(AuthorizationError):
        await svc.delete(CID, t.id, OTHER)
    await svc.delete(CID, t.id, AUTHOR)
    repo.soft_delete.assert_awaited_once_with(t)


async def test_clone_freezes_schema_and_items(parts):
    svc, repo, _, lists, items = parts
    t = _tpl()
    t.is_shared, t.is_system = False, False
    repo.get_by_id.return_value = t
    new = await svc.clone_template_to_list(CID, t.id, AUTHOR, title="L", visibility="private")
    assert new.template_id == t.id
    assert new.field_schema == [
        {"key": "k", "label": "K", "type_key": "select", "required": True, "config": {"options": []}}
    ]
    assert new.item_count == 1
    items.create.assert_awaited_once()


async def test_clone_without_items(parts):
    svc, repo, _, lists, items = parts
    t = _tpl()
    repo.get_by_id.return_value = t
    new = await svc.clone_template_to_list(CID, t.id, AUTHOR, include_items=False)
    assert new.item_count == 0 and new.title == t.name
    items.create.assert_not_called()
