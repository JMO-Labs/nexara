"""
@file crud.py
@brief Subgroup CRUD operations — create, read, list, update, archive.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.i18n import _
from app.models.subgroup import ChatChannel, Subgroup
from app.models.user import User
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.subgroups.helpers import is_admin, require_role

logger = structlog.get_logger(__name__)


class SubgroupCrudMixin:
    """
    @brief Mixin exposing subgroup CRUD operations.

    Expected attributes on the host class:
      - ``_subgroup_repo`` — :class:`SubgroupRepository`
      - ``_member_repo`` — :class:`SubgroupMemberRepository`
      - ``_community_id`` — community UUID
    """

    _subgroup_repo: SubgroupRepository
    _member_repo: SubgroupMemberRepository
    _community_id: uuid.UUID

    async def create_subgroup(
        self,
        user: User,
        *,
        name: str,
        slug: str,
        description: str | None = None,
        avatar_url: str | None = None,
        is_private: bool = False,
        join_policy: str = "open",
    ) -> tuple[Subgroup, ChatChannel]:
        """
        @brief Create a new subgroup.

        Enforces slug uniqueness, auto-adds the creator as ``owner``,
        and inserts the associated chat channel row.

        @param user The authenticated user creating the subgroup.
        @param name Subgroup display name.
        @param slug URL-safe unique identifier.
        @param description Optional description.
        @param avatar_url Optional avatar URL.
        @param is_private Hide from public discovery when true.
        @param join_policy One of ``open``/``invite_only``/``admin_approval``.
        @return Tuple of (Subgroup, ChatChannel).
        @raises ConflictError If a subgroup with this slug exists.
        """
        existing = await self._subgroup_repo.get_by_slug(slug, self._community_id)
        if existing is not None:
            raise ConflictError(message=_("A subgroup with this slug already exists"))

        subgroup = await self._subgroup_repo.create_subgroup(
            community_id=self._community_id,
            name=name,
            slug=slug,
            description=description,
            avatar_url=avatar_url,
            is_private=is_private,
            join_policy=join_policy,
            created_by=user.id,
        )

        await self._member_repo.add_member(
            community_id=self._community_id,
            subgroup_id=subgroup.id,
            user_id=user.id,
            role="owner",
        )

        channel = await self._subgroup_repo.create_chat_channel(
            community_id=self._community_id,
            subgroup_id=subgroup.id,
            name=name,
        )

        logger.info(
            "subgroup_created",
            subgroup_id=str(subgroup.id),
            slug=slug,
            created_by=str(user.id),
        )
        return subgroup, channel

    async def get_subgroup(self, slug: str, user: User) -> Subgroup:
        """
        @brief Fetch a subgroup by slug, enforcing visibility rules.

        Private subgroups are visible only to members or admins.

        @param slug Subgroup slug.
        @param user Requesting user.
        @return The Subgroup ORM instance.
        @raises NotFoundError If not found or not visible.
        """
        subgroup = await self._subgroup_repo.get_by_slug(slug, self._community_id)
        if subgroup is None:
            raise NotFoundError(message=_("Subgroup not found"))

        if subgroup.is_private and not is_admin(user):
            membership = await self._member_repo.get_membership(subgroup.id, user.id)
            if membership is None:
                raise NotFoundError(message=_("Subgroup not found"))

        return subgroup

    async def list_subgroups(self, user: User) -> list[Subgroup]:
        """
        @brief List subgroups visible to the requesting user.

        @param user Requesting user.
        @return List of Subgroup rows.
        """
        return await self._subgroup_repo.list_visible_for_user(
            self._community_id,
            user.id,
            is_admin=is_admin(user),
        )

    async def update_subgroup(
        self,
        slug: str,
        user: User,
        updates: dict[str, Any],
    ) -> Subgroup:
        """
        @brief Update subgroup fields (owner/moderator/admin only).

        @param slug Subgroup slug.
        @param user Acting user.
        @param updates Dict of field updates.
        @return The updated Subgroup.
        @raises NotFoundError If subgroup not found.
        @raises AuthorizationError If user lacks permission or subgroup
            is archived.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(self._member_repo, subgroup, user, {"owner", "moderator"})

        if subgroup.archived_at is not None and not is_admin(user):
            raise AuthorizationError(message=_("Archived subgroups are read-only"))

        return await self._subgroup_repo.update_fields(subgroup, updates)

    async def archive_subgroup(self, slug: str, user: User) -> Subgroup:
        """
        @brief Archive a subgroup (owner or admin only).

        @param slug Subgroup slug.
        @param user Requesting user.
        @return The archived Subgroup.
        @raises NotFoundError If subgroup not found.
        @raises AuthorizationError If user is not owner or admin.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(self._member_repo, subgroup, user, {"owner"})
        return await self._subgroup_repo.archive(subgroup)
