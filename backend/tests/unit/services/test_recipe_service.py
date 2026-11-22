"""
@file test_recipe_service.py
@brief Unit tests for RecipeService (AsyncMock repos).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError as PydanticError

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.models.community import Community
from app.models.recipe import Recipe
from app.repositories.community_repo import CommunityRepository
from app.repositories.recipe_repo import RecipeRepository
from app.schemas.recipe import Ingredient, RecipeCreate
from app.services.mention_tags import MentionTagsService
from app.services.recipe_service import RecipeService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR, OTHER = uuid.uuid4(), uuid.uuid4()


def _row(author: uuid.UUID = AUTHOR) -> MagicMock:
    r = MagicMock(spec=Recipe)
    r.id, r.author_id, r.story = uuid.uuid4(), author, "Thanks @maya"
    r.title, r.ingredients, r.steps = "Cornbread", [{"qty": "1", "item": "cornmeal"}], ["Bake"]
    r.servings = r.prep_minutes = r.cook_minutes = None
    r.photo_media_ids, r.tags, r.visibility, r.subgroup_id = [], [], "community", None
    r.best_maker_user_id = r.best_maker_household_id = None
    r.created_at = r.updated_at = datetime.now(UTC)
    return r


@pytest.fixture
def svc():
    repo = AsyncMock(spec=RecipeRepository)
    comm = AsyncMock(spec=CommunityRepository)
    community = MagicMock(spec=Community)
    community.features = {}
    comm.get.return_value = community
    repo.author_names.return_value = {AUTHOR: "Ruth"}
    repo.household_names.return_value = {}
    repo.own_media_count.return_value = 0
    mentions = AsyncMock(spec=MentionTagsService)
    return RecipeService(repo, comm, mentions, None, CID), repo, community, mentions


def _body(**kw) -> RecipeCreate:
    return RecipeCreate(**{"title": "Cornbread", **kw})


async def test_create_syncs_mentions_and_returns(svc):
    s, repo, _, mentions = svc
    repo.create.return_value = _row()
    out = await s.create(AUTHOR, _body(tags=[" Dinner ", "dinner"], steps=[" a ", " "]))
    data = repo.create.call_args.args[2]
    assert data["tags"] == ["dinner"] and data["steps"] == ["a"]
    assert out.author.display_name == "Ruth"
    assert mentions.sync_mentions.call_args.args[1] == "recipe"


def test_more_than_100_ingredients_rejected():
    with pytest.raises(PydanticError):
        _body(ingredients=[Ingredient(item="x")] * 101)


async def test_foreign_photos_rejected(svc):
    s, repo, _, _ = svc
    repo.own_media_count.return_value = 0
    with pytest.raises(AppError) as e:
        await s.create(AUTHOR, _body(photo_media_ids=[uuid.uuid4()]))
    assert e.value.status_code == 422


async def test_subgroup_requires_membership(svc):
    s, repo, _, _ = svc
    repo.is_group_member.return_value = False
    with pytest.raises(AppError):
        await s.create(AUTHOR, _body(visibility="subgroup", subgroup_id=uuid.uuid4()))


async def test_get_hidden_is_not_found(svc):
    s, repo, _, _ = svc
    repo.get_visible.return_value = None
    with pytest.raises(NotFoundError):
        await s.get(uuid.uuid4(), OTHER)


async def test_update_by_non_author_forbidden_but_admin_allowed(svc):
    s, repo, _, _ = svc
    row = _row()
    repo.get.return_value = row
    repo.get_visible.return_value = row
    with pytest.raises(AuthorizationError):
        await s.update(row.id, OTHER, _body(), is_admin=False)
    repo.apply.return_value = row
    await s.update(row.id, OTHER, _body(), is_admin=True)
    repo.apply.assert_awaited_once()


async def test_delete_hidden_recipe_not_found(svc):
    s, repo, _, _ = svc
    row = _row()
    repo.get.return_value = row
    repo.get_visible.return_value = None
    with pytest.raises(NotFoundError):
        await s.delete(row.id, OTHER, is_admin=False)


async def test_delete_author(svc):
    s, repo, _, _ = svc
    row = _row()
    repo.get.return_value = row
    await s.delete(row.id, AUTHOR, is_admin=False)
    repo.soft_delete.assert_awaited_once()


async def test_feature_off_404(svc):
    s, _, community, _ = svc
    community.features = {"recipes": False}
    with pytest.raises(AppError) as e:
        await s.list(AUTHOR)
    assert e.value.status_code == 404


async def test_list_paginates(svc):
    s, repo, _, _ = svc
    repo.list_page.return_value = [_row() for _ in range(25)]
    repo.cursor_for = MagicMock(return_value="c")
    page = await s.list(AUTHOR, q="corn")
    assert len(page.recipes) == 24 and page.next_cursor == "c"
