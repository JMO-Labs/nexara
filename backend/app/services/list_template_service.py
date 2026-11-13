"""
@file list_template_service.py
@brief Business logic for list template CRUD and template-to-list cloning.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.list import List, ListItem
from app.models.list_template import ListTemplate, ListTemplateField, ListTemplateItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_template_repo import ListTemplateRepository
from app.services.list_field_registry import FieldTypeNotFound, ListFieldRegistry

_UPDATABLE = ("name", "description", "category", "icon", "color", "cover_media_id", "is_shared")


class ListTemplateService:
    """@brief Template CRUD with registry-validated fields and author-only writes."""

    def __init__(
        self,
        repo: ListTemplateRepository,
        field_registry: ListFieldRegistry,
        list_repo: ListRepository | None = None,
        item_repo: ListItemRepository | None = None,
    ) -> None:
        """
        @param repo Template repository.
        @param field_registry Field-type registry used to validate configs.
        @param list_repo List repository (required for cloning).
        @param item_repo List item repository (required for cloning items).
        """
        self._repo = repo
        self._registry = field_registry
        self._lists = list_repo
        self._items = item_repo

    def _validate_fields(self, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """@brief Validate each field config; convert registry errors to AppError."""
        out: list[dict[str, Any]] = []
        for f in fields:
            try:
                config = self._registry.validate_config(f["type_key"], f.get("config") or {})
            except FieldTypeNotFound as exc:
                raise ValidationError(
                    _("Unknown field type"), {"field": f.get("key"), "type_key": str(exc)}
                ) from exc
            except ValueError as exc:
                raise ValidationError(
                    _("Invalid field configuration"), {"field": f.get("key"), "reason": str(exc)}
                ) from exc
            out.append({**f, "config": config})
        return out

    @staticmethod
    def _build_fields(fields: list[dict[str, Any]]) -> list[ListTemplateField]:
        return [
            ListTemplateField(
                position=i,
                key=f["key"],
                label=f["label"],
                type_key=f["type_key"],
                required=f.get("required", False),
                config=f["config"],
            )
            for i, f in enumerate(fields)
        ]

    @staticmethod
    def _build_items(items: list[dict[str, Any]]) -> list[ListTemplateItem]:
        return [
            ListTemplateItem(position=i, values=it.get("values", {})) for i, it in enumerate(items)
        ]

    async def create(
        self, community_id: uuid.UUID, author_id: uuid.UUID, data: dict[str, Any]
    ) -> ListTemplate:
        """
        @brief Create a template with its fields and starter items.

        @param data Template attrs plus optional ``fields`` and ``items`` lists.
        @return The persisted template.
        @throws AppError If a field config is invalid.
        """
        fields = self._validate_fields(data.get("fields", []))
        tpl = ListTemplate(
            community_id=community_id,
            author_id=author_id,
            **{k: data[k] for k in _UPDATABLE if k in data},
        )
        tpl.fields = self._build_fields(fields)
        tpl.items = self._build_items(data.get("items", []))
        return await self._repo.create(tpl)

    async def list_for_community(
        self,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[ListTemplate], str | None]:
        """@brief Keyset page of templates owned by or shared with the viewer."""
        return await self._repo.list_for_community(
            community_id, viewer_id, cursor=cursor, limit=limit
        )

    async def _load(self, community_id: uuid.UUID, template_id: uuid.UUID) -> ListTemplate:
        tpl = await self._repo.get_by_id(template_id, community_id)
        if tpl is None or tpl.deleted_at is not None:
            raise NotFoundError(_("Template not found"))
        return tpl

    async def get_by_id(
        self, community_id: uuid.UUID, template_id: uuid.UUID, viewer_id: uuid.UUID
    ) -> ListTemplate:
        """
        @brief Fetch a template visible to the viewer.
        @throws NotFoundError If missing, soft-deleted or not visible.
        """
        tpl = await self._load(community_id, template_id)
        if tpl.author_id != viewer_id and not (tpl.is_shared or tpl.is_system):
            raise NotFoundError(_("Template not found"))
        return tpl

    async def _load_owned(
        self, community_id: uuid.UUID, template_id: uuid.UUID, user_id: uuid.UUID
    ) -> ListTemplate:
        tpl = await self._load(community_id, template_id)
        if tpl.author_id != user_id:
            raise AuthorizationError(_("Only the author can modify this template"))
        return tpl

    async def update(
        self,
        community_id: uuid.UUID,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> ListTemplate:
        """
        @brief Update template attrs and optionally replace fields/items.
        @throws AuthorizationError If the user is not the author.
        @throws AppError If new field configs are invalid.
        """
        tpl = await self._load_owned(community_id, template_id, user_id)
        changes: dict[str, Any] = {k: data[k] for k in _UPDATABLE if k in data}
        if "fields" in data:
            changes["fields"] = self._build_fields(self._validate_fields(data["fields"]))
        if "items" in data:
            changes["items"] = self._build_items(data["items"])
        return await self._repo.update(tpl, changes)

    async def delete(
        self, community_id: uuid.UUID, template_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """
        @brief Soft-delete a template.
        @throws AuthorizationError If the user is not the author.
        """
        tpl = await self._load_owned(community_id, template_id, user_id)
        await self._repo.soft_delete(tpl)

    async def clone_template_to_list(
        self,
        community_id: uuid.UUID,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        title: str | None = None,
        visibility: str = "private",
        include_items: bool = True,
    ) -> List:
        """
        @brief Instantiate a template as a new list with a frozen field_schema.

        @param include_items Also copy template items as list items.
        @return The new list.
        """
        if self._lists is None or self._items is None:
            raise AppError("INTERNAL_ERROR", _("List repositories not configured"))
        tpl = await self.get_by_id(community_id, template_id, user_id)
        schema = [
            {
                "key": f.key,
                "label": f.label,
                "type_key": f.type_key,
                "required": f.required,
                "config": dict(f.config),
            }
            for f in tpl.fields
        ]
        src = list(tpl.items) if include_items else []
        new = List(
            community_id=community_id,
            template_id=tpl.id,
            owner_id=user_id,
            title=title or tpl.name,
            description=tpl.description,
            visibility=visibility,
            field_schema=schema,
            item_count=len(src),
        )
        new = await self._lists.create(new)
        for it in src:
            await self._items.create(
                ListItem(list_id=new.id, position=it.position, values=dict(it.values))
            )
        return new
