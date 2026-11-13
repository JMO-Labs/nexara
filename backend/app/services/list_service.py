"""
@file list_service.py
@brief ListService: list CRUD, visibility enforcement and member operations.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthorizationError, NotFoundError
from app.core.i18n import _
from app.models.list import List
from app.models.subgroup import SubgroupMember
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.services.list_field_registry import ListFieldRegistry

WRITABLE_FIELDS = ("title", "description", "color", "expires_at")
VISIBILITIES = ("community", "subgroup", "private", "members")


class ListService:
    """@brief Service layer for lists and explicit list membership."""

    def __init__(
        self,
        repo_list: ListRepository,
        repo_member: ListMemberRepository,
        field_registry: ListFieldRegistry,
        community_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        """
        @param repo_list List repository.
        @param repo_member List member repository.
        @param field_registry Field type registry (for field_schema validation).
        @param community_id Tenant scope.
        @param session Request-scoped async session.
        """
        self._lists = repo_list
        self._members = repo_member
        self._registry = field_registry
        self._community_id = community_id
        self._session = session

    async def _subgroup_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Subgroups the user belongs to (descendants included)."""
        from app.repositories.subgroup_repo import expand_with_descendants

        stmt = select(SubgroupMember.subgroup_id).where(SubgroupMember.user_id == user_id)
        direct = list((await self._session.execute(stmt)).scalars().all())
        return await expand_with_descendants(self._session, direct)

    async def _can_view(self, lst: List, user_id: uuid.UUID) -> bool:
        """@brief community: all; private: owner; subgroup: member; members: listed or owner."""
        if lst.visibility == "community":
            return True
        if lst.visibility == "private":
            return lst.owner_id == user_id
        if lst.visibility == "subgroup":
            if lst.subgroup_id is None:
                return False
            return lst.subgroup_id in await self._subgroup_ids(user_id)
        if lst.visibility == "members":
            if lst.owner_id == user_id:
                return True
            return await self._members.get_member(lst.id, user_id) is not None
        return False

    async def _can_edit(self, lst: List, user_id: uuid.UUID, is_admin: bool = False) -> bool:
        """@brief Owner, global admin, or list member with role 'admin'."""
        if lst.owner_id == user_id or is_admin:
            return True
        member = await self._members.get_member(lst.id, user_id)
        return member is not None and member.role == "admin"

    async def _load_viewable(self, list_id: uuid.UUID, user_id: uuid.UUID) -> List:
        lst = await self._lists.get_by_id(list_id, self._community_id)
        if lst is None or not await self._can_view(lst, user_id):
            raise NotFoundError(_("List not found"))
        return lst

    async def _load_editable(
        self, list_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool = False
    ) -> List:
        lst = await self._load_viewable(list_id, user_id)
        if not await self._can_edit(lst, user_id, is_admin):
            raise AuthorizationError(_("Not allowed to modify this list"))
        return lst

    async def create(
        self,
        owner_id: uuid.UUID,
        *,
        title: str,
        visibility: str,
        description: str | None = None,
        subgroup_id: uuid.UUID | None = None,
        template_id: uuid.UUID | None = None,
        field_schema: list[dict[str, Any]] | None = None,
        expires_at: Any = None,
    ) -> List:
        """
        @brief Create a list with zeroed counters.

        @param owner_id Creating user.
        @param field_schema Optional initial schema; each field's config is validated.
        @return Persisted List.
        @raises AppError On invalid visibility / subgroup combination or field config.
        """
        if visibility not in VISIBILITIES:
            raise AppError("VALIDATION_ERROR", _("Invalid visibility"), 422)
        if visibility == "subgroup" and subgroup_id is None:
            raise AppError("VALIDATION_ERROR", _("subgroup_id required"), 422)
        schema = list(field_schema or [])
        for field in schema:
            try:
                self._registry.validate_config(field["type"], field.get("config", {}))
            except (KeyError, ValueError) as exc:
                raise AppError("VALIDATION_ERROR", _("Invalid field schema"), 422) from exc
        lst = List(
            community_id=self._community_id,
            owner_id=owner_id,
            title=title,
            description=description,
            visibility=visibility,
            subgroup_id=subgroup_id if visibility == "subgroup" else None,
            template_id=template_id,
            expires_at=expires_at,
            status="active",
            field_schema=schema,
            item_count=0,
            completed_count=0,
            signup_count=0,
        )
        return await self._lists.create(lst)

    async def list_visible(
        self, viewer_id: uuid.UUID, cursor: str | None = None, limit: int = 20
    ) -> tuple[list[List], str | None]:
        """@brief Keyset page of lists visible to the viewer."""
        return await self._lists.list_visible(
            self._community_id,
            viewer_id,
            subgroup_ids=await self._subgroup_ids(viewer_id),
            cursor=cursor,
            limit=limit,
        )

    async def get_by_id(self, list_id: uuid.UUID, viewer_id: uuid.UUID) -> List:
        """@raises NotFoundError When missing or not visible."""
        return await self._load_viewable(list_id, viewer_id)

    async def update(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        is_admin: bool = False,
    ) -> List:
        """@brief Update writable fields (title/description/color/expires_at)."""
        lst = await self._load_editable(list_id, user_id, is_admin)
        changes = {k: v for k, v in data.items() if k in WRITABLE_FIELDS}
        return await self._lists.update(lst, changes)

    async def delete(self, list_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool = False) -> None:
        """@brief Soft-delete; owner only (is_admin accepted but not sufficient)."""
        lst = await self._load_viewable(list_id, user_id)
        if lst.owner_id != user_id:
            raise AuthorizationError(_("Only the owner can delete this list"))
        await self._lists.soft_delete(lst)

    async def archive(
        self, list_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool = False
    ) -> List:
        """@brief Set status='archived'."""
        lst = await self._load_editable(list_id, user_id, is_admin)
        return await self._lists.update(lst, {"status": "archived"})

    async def _load_members_list(
        self, list_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool
    ) -> List:
        lst = await self._load_editable(list_id, user_id, is_admin)
        if lst.visibility != "members":
            raise AppError("VALIDATION_ERROR", _("List does not use explicit members"), 422)
        return lst

    async def add_member(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        member_id: uuid.UUID,
        role: str = "viewer",
        is_admin: bool = False,
    ) -> Any:
        """@brief Add a member to a visibility='members' list."""
        lst = await self._load_members_list(list_id, user_id, is_admin)
        if await self._members.get_member(lst.id, member_id) is not None:
            raise AppError("CONFLICT", _("Already a member"), 409)
        return await self._members.add_member(lst.id, member_id, role)

    async def remove_member(
        self,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        member_id: uuid.UUID,
        is_admin: bool = False,
    ) -> None:
        """@brief Remove a member from a visibility='members' list."""
        lst = await self._load_members_list(list_id, user_id, is_admin)
        member = await self._members.get_member(lst.id, member_id)
        if member is None:
            raise NotFoundError(_("Member not found"))
        await self._members.remove_member(member)

    async def update_member_share(
        self, list_id: uuid.UUID, user_id: uuid.UUID, share_personal: bool
    ) -> Any:
        """@brief A member toggles sharing of their personal data (self only)."""
        lst = await self._load_viewable(list_id, user_id)
        member = await self._members.get_member(lst.id, user_id)
        if member is None:
            raise NotFoundError(_("Member not found"))
        return await self._members.update_member(member, {"share_personal": share_personal})
