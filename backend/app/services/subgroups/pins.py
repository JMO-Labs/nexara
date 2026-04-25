"""
@file pins.py
@brief Pinned-post operations for subgroups.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update

from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.post import Post
from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository
from app.services.subgroups.helpers import require_role


class SubgroupPinsMixin:
    """
    @brief Mixin exposing pin/unpin operations for subgroup posts.

    Expected attributes:
      - ``_post_repo``, ``_member_repo``, ``_community_id``
    """

    _post_repo: PostRepository
    _member_repo: SubgroupMemberRepository
    _community_id: uuid.UUID

    async def get_subgroup(self, slug: str, user: User) -> Any:  # noqa: D401
        """@brief Implemented in :class:`SubgroupCrudMixin`."""
        raise NotImplementedError

    async def pin_post(
        self,
        slug: str,
        post_id: uuid.UUID,
        user: User,
    ) -> dict[str, Any]:
        """
        @brief Pin a post as the subgroup announcement.

        Unsets any previously pinned post in the same subgroup so that
        only one post is pinned at a time. The post must belong to the
        subgroup.

        @param slug Subgroup slug.
        @param post_id Post UUID to pin.
        @param user Requesting user.
        @return Dict with ``post_id`` and ``subgroup_id``.
        @raises NotFoundError If subgroup or post not found.
        @raises AuthorizationError If user lacks permission.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(
            self._member_repo, self._subgroup_repo, subgroup, user, {"owner", "moderator"}
        )

        post = await self._post_repo.get_by_id(post_id, community_id=self._community_id)
        if post is None or post.subgroup_id != subgroup.id:
            raise NotFoundError(message=_("Post not found in this subgroup"))

        session = self._post_repo._session
        await session.execute(
            update(Post)
            .where(
                Post.subgroup_id == subgroup.id,
                Post.is_pinned.is_(True),
                Post.id != post_id,
            )
            .values(is_pinned=False),
        )

        post.is_pinned = True
        await session.flush()
        return {"post_id": str(post.id), "subgroup_id": str(subgroup.id)}

    async def unpin_post(self, slug: str, user: User) -> None:
        """
        @brief Remove any pinned post from a subgroup.

        @param slug Subgroup slug.
        @param user Requesting user.
        @raises NotFoundError If subgroup missing.
        @raises AuthorizationError If user lacks permission.
        """
        subgroup = await self.get_subgroup(slug, user)
        await require_role(
            self._member_repo, self._subgroup_repo, subgroup, user, {"owner", "moderator"}
        )

        session = self._post_repo._session
        await session.execute(
            update(Post)
            .where(Post.subgroup_id == subgroup.id, Post.is_pinned.is_(True))
            .values(is_pinned=False),
        )

    async def get_pinned_post_id(self, subgroup_id: uuid.UUID) -> uuid.UUID | None:
        """
        @brief Return the pinned post ID for a subgroup, if any.

        @param subgroup_id Subgroup ID.
        @return Post UUID or None.
        """
        session = self._post_repo._session
        stmt = select(Post.id).where(
            Post.subgroup_id == subgroup_id,
            Post.is_pinned.is_(True),
            Post.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
