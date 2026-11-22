"""
@file recipe_repo.py
@brief Data access for recipes: viewer-scoped reads, FTS search, tag counts
       and the validation lookups (own media, visible makers, group membership).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.list import ListItem
from app.models.media import Media
from app.models.recipe import Recipe
from app.models.subgroup import SubgroupMember
from app.models.user import User
from app.repositories.household_repo import household_visible
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt
from app.repositories.visibility_preds import my_subgroup_ids, not_blocked, recipe_visible


class RecipeRepository:
    """@brief Async repository for Recipe."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, community_id: uuid.UUID, author_id: uuid.UUID, data: dict[str, Any]
    ) -> Recipe:
        """@brief Insert and return a recipe."""
        row = Recipe(community_id=community_id, author_id=author_id, **data)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, recipe_id: uuid.UUID, community_id: uuid.UUID) -> Recipe | None:
        """@brief Live recipe by id regardless of viewer (for author/admin checks)."""
        stmt = select(Recipe).where(
            Recipe.id == recipe_id, Recipe.community_id == community_id, Recipe.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_visible(
        self, recipe_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> Recipe | None:
        """@brief Recipe by id only if the viewer may read it."""
        stmt = select(Recipe).where(
            Recipe.id == recipe_id,
            recipe_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_page(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        q: str | None,
        tag: str | None,
        cursor: str | None,
        limit: int,
    ) -> list[Recipe]:
        """@brief Up to ``limit + 1`` visible recipes, newest first (keyset)."""
        stmt = select(Recipe).where(
            recipe_visible(viewer_id, my_subgroup_ids(viewer_id), community_id)
        )
        if q and q.strip():
            stmt = stmt.where(
                Recipe.search_fts.op("@@")(func.websearch_to_tsquery("english", q.strip()))
            )
        if tag:
            stmt = stmt.where(Recipe.tags.contains([tag]))
        at = decode_cursor(cursor, parse_dt)
        if at is not None:
            stmt = stmt.where(
                (Recipe.created_at < at[0]) | ((Recipe.created_at == at[0]) & (Recipe.id < at[1]))
            )
        stmt = stmt.order_by(Recipe.created_at.desc(), Recipe.id.desc()).limit(limit + 1)
        return list((await self._session.execute(stmt)).scalars())

    @staticmethod
    def cursor_for(row: Recipe) -> str:
        """@return Opaque cursor pointing after ``row``."""
        return encode_cursor(row.created_at, row.id)

    async def tag_counts(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> list[tuple[str, int]]:
        """@brief Distinct tags across visible recipes with counts."""
        t = func.unnest(Recipe.tags).label("tag")
        sub = (
            select(t)
            .where(recipe_visible(viewer_id, my_subgroup_ids(viewer_id), community_id))
            .subquery()
        )
        stmt = (
            select(sub.c.tag, func.count())
            .group_by(sub.c.tag)
            .order_by(func.count().desc(), sub.c.tag)
        )
        return [(a, int(b)) for a, b in (await self._session.execute(stmt)).all()]

    async def recent_visible(
        self, viewer_id: uuid.UUID, community_id: uuid.UUID, since: datetime, limit: int = 10
    ) -> list[Recipe]:
        """@brief Visible recipes created since ``since`` by other people (recap)."""
        stmt = (
            select(Recipe)
            .where(
                recipe_visible(viewer_id, my_subgroup_ids(viewer_id), community_id),
                Recipe.created_at >= since,
                Recipe.author_id != viewer_id,
            )
            .order_by(Recipe.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def apply(self, row: Recipe, data: dict[str, Any], now: datetime) -> Recipe:
        """@brief Set fields on ``row`` and flush."""
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = now
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def soft_delete(self, row: Recipe, now: datetime) -> None:
        """@brief Soft-delete and unlink every list item that pointed at it."""
        row.deleted_at = now
        await self._session.execute(
            update(ListItem).where(ListItem.recipe_id == row.id).values(recipe_id=None)
        )
        await self._session.flush()

    async def own_media_count(
        self, ids: list[uuid.UUID], author_id: uuid.UUID, community_id: uuid.UUID
    ) -> int:
        """@brief How many of ``ids`` are the author's own media."""
        stmt = select(func.count(Media.id)).where(
            Media.id.in_(ids), Media.uploader_id == author_id, Media.community_id == community_id
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def is_live_user(
        self, user_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief User exists in the community and is not blocked either way."""
        stmt = select(User.id).where(
            User.id == user_id,
            User.community_id == community_id,
            User.deleted_at.is_(None),
            not_blocked(User.id, viewer_id),
        )
        return (await self._session.execute(stmt)).first() is not None

    async def is_visible_household(
        self, member_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> bool:
        """@brief Household member the viewer may see."""
        stmt = select(HouseholdMember.id).where(
            HouseholdMember.id == member_id, household_visible(viewer_id, community_id)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def is_group_member(self, subgroup_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief User belongs to the subgroup."""
        stmt = select(SubgroupMember.user_id).where(
            SubgroupMember.subgroup_id == subgroup_id, SubgroupMember.user_id == user_id
        )
        return (await self._session.execute(stmt)).first() is not None

    async def author_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@brief Display names keyed by user id."""
        if not ids:
            return {}
        stmt = select(User.id, User.display_name).where(User.id.in_(ids))
        return {i: n for i, n in (await self._session.execute(stmt)).all()}

    async def household_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@brief Household member names keyed by id."""
        if not ids:
            return {}
        stmt = select(HouseholdMember.id, HouseholdMember.name).where(HouseholdMember.id.in_(ids))
        return {i: n for i, n in (await self._session.execute(stmt)).all()}
