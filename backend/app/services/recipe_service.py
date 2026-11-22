"""
@file recipe_service.py
@brief Family recipe book: create/update/delete (author or admin), viewer-aware
       list/get, tag counts and @mention sync on the story.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.recipe import Recipe
from app.repositories.community_repo import CommunityRepository
from app.repositories.recipe_repo import RecipeRepository
from app.schemas.recipe import (
    RecipeAuthor,
    RecipeBase,
    RecipeOut,
    RecipePage,
    TagCount,
)
from app.services.mention_tags import MentionTagsService
from app.services.notification_service import NotificationService

PAGE = 24


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, 422)


class RecipeService:
    """@brief Business rules for recipes."""

    def __init__(
        self,
        repo: RecipeRepository,
        community_repo: CommunityRepository,
        mention_tags: MentionTagsService,
        notifications: NotificationService | None,
        community_id: uuid.UUID,
    ) -> None:
        self._repo = repo
        self._communities = community_repo
        self._mentions = mention_tags
        self._notify = notifications
        self._community_id = community_id

    async def _require_feature(self) -> None:
        community = await self._communities.get(self._community_id)
        if community is not None:
            require_feature(community, "recipes")

    async def _clean(self, body: RecipeBase, user_id: uuid.UUID) -> dict[str, Any]:
        """@brief Validate references and return column values."""
        data = body.model_dump()
        data["title"] = body.title.strip()
        data["steps"] = [s.strip() for s in body.steps if s.strip()]
        data["tags"] = list(dict.fromkeys(t.strip().lower() for t in body.tags if t.strip()))
        data["photo_media_ids"] = list(dict.fromkeys(body.photo_media_ids))
        photos = data["photo_media_ids"]
        if photos and await self._repo.own_media_count(photos, user_id, self._community_id) != len(
            photos
        ):
            raise _invalid(_("You can only attach your own photos"))
        if body.visibility == "subgroup":
            if body.subgroup_id is None or not await self._repo.is_group_member(
                body.subgroup_id, user_id
            ):
                raise _invalid(_("Pick a group you belong to"))
        else:
            data["subgroup_id"] = None
        if body.best_maker_user_id and not await self._repo.is_live_user(
            body.best_maker_user_id, user_id, self._community_id
        ):
            raise _invalid(_("Unknown best maker"))
        if body.best_maker_household_id and not await self._repo.is_visible_household(
            body.best_maker_household_id, user_id, self._community_id
        ):
            raise _invalid(_("Unknown best maker"))
        return data

    async def _sync(self, row: Recipe, actor_id: uuid.UUID, *, fresh: bool) -> None:
        await self._mentions.sync_mentions(
            self._community_id,
            "recipe",
            row.id,
            row.story,
            actor_id,
            None,
            notify_callable=self._notify.notify if self._notify else None,
            can_see=lambda uid: self._can_see(row.id, uid),
            link=f"/app/recipes/{row.id}",
            label=_("a recipe"),
            fresh=fresh,
        )

    async def _can_see(self, recipe_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self._repo.get_visible(recipe_id, user_id, self._community_id) is not None

    async def _out(self, rows: list[Recipe]) -> list[RecipeOut]:
        users = {r.author_id for r in rows} | {
            r.best_maker_user_id for r in rows if r.best_maker_user_id
        }
        names = await self._repo.author_names(list(users))
        hh = await self._repo.household_names(
            [r.best_maker_household_id for r in rows if r.best_maker_household_id]
        )
        out: list[RecipeOut] = []
        for r in rows:
            maker = (
                names.get(r.best_maker_user_id)
                if r.best_maker_user_id
                else hh.get(r.best_maker_household_id)
                if r.best_maker_household_id
                else None
            )
            out.append(
                RecipeOut.model_validate(
                    {
                        **{f: getattr(r, f) for f in RecipeBase.model_fields},
                        "id": r.id,
                        "author": RecipeAuthor(
                            id=r.author_id, display_name=names.get(r.author_id, "")
                        ),
                        "best_maker_name": maker,
                        "created_at": r.created_at,
                        "updated_at": r.updated_at,
                    }
                )
            )
        return out

    async def create(self, user_id: uuid.UUID, body: RecipeBase) -> RecipeOut:
        """@raises AppError 422 on bad photos, group or maker."""
        await self._require_feature()
        row = await self._repo.create(self._community_id, user_id, await self._clean(body, user_id))
        await self._sync(row, user_id, fresh=True)
        return (await self._out([row]))[0]

    async def update(
        self, recipe_id: uuid.UUID, user_id: uuid.UUID, body: RecipeBase, *, is_admin: bool
    ) -> RecipeOut:
        """@raises AuthorizationError unless author or admin."""
        await self._require_feature()
        row = await self._owned(recipe_id, user_id, is_admin)
        data = await self._clean(body, row.author_id)
        row = await self._repo.apply(row, data, datetime.now(UTC))
        await self._sync(row, user_id, fresh=False)
        return (await self._out([row]))[0]

    async def _owned(self, recipe_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> Recipe:
        row = await self._repo.get(recipe_id, self._community_id)
        if row is None or (row.author_id != user_id and not is_admin):
            if row is not None and await self._can_see(recipe_id, user_id):
                raise AuthorizationError(_("Only the author can change a recipe"))
            raise NotFoundError(_("Recipe not found"))
        return row

    async def delete(self, recipe_id: uuid.UUID, user_id: uuid.UUID, *, is_admin: bool) -> None:
        """@brief Soft-delete (author or admin); unlinks list items."""
        await self._require_feature()
        row = await self._owned(recipe_id, user_id, is_admin)
        await self._repo.soft_delete(row, datetime.now(UTC))

    async def get(self, recipe_id: uuid.UUID, viewer_id: uuid.UUID) -> RecipeOut:
        """@raises NotFoundError when missing or not visible to the viewer."""
        await self._require_feature()
        row = await self._repo.get_visible(recipe_id, viewer_id, self._community_id)
        if row is None:
            raise NotFoundError(_("Recipe not found"))
        return (await self._out([row]))[0]

    async def tags(self, viewer_id: uuid.UUID) -> list[TagCount]:
        """@return Distinct tags on visible recipes with counts."""
        await self._require_feature()
        found = await self._repo.tag_counts(viewer_id, self._community_id)
        return [TagCount(tag=t, count=c) for t, c in found]

    async def list(
        self,
        viewer_id: uuid.UUID,
        q: str | None = None,
        tag: str | None = None,
        cursor: str | None = None,
    ) -> RecipePage:
        """@return Page of visible recipes (search over title, story, ingredients)."""
        await self._require_feature()
        rows = await self._repo.list_page(
            viewer_id, self._community_id, q=q, tag=tag, cursor=cursor, limit=PAGE
        )
        more = len(rows) > PAGE
        rows = rows[:PAGE]
        return RecipePage(
            recipes=await self._out(rows),
            next_cursor=self._repo.cursor_for(rows[-1]) if more else None,
        )
