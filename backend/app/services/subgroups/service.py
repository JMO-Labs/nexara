"""
@file service.py
@brief Facade class composing the subgroup service mixins.
"""

from __future__ import annotations

import uuid

from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.subgroups.crud import SubgroupCrudMixin
from app.services.subgroups.membership import SubgroupMembershipMixin
from app.services.subgroups.pins import SubgroupPinsMixin


class SubgroupService(
    SubgroupCrudMixin,
    SubgroupMembershipMixin,
    SubgroupPinsMixin,
):
    """
    @brief Service layer for subgroups, membership, and pinned posts.

    Composes :class:`SubgroupCrudMixin`,
    :class:`SubgroupMembershipMixin`, and :class:`SubgroupPinsMixin`
    so callers see a single cohesive service.

    @param subgroup_repo Subgroup repository.
    @param member_repo Subgroup member repository.
    @param post_repo Post repository (used by the pin mixin).
    @param community_id Community scope (UUID).
    @param max_memberships_per_user Maximum active memberships per user.
    """

    def __init__(
        self,
        subgroup_repo: SubgroupRepository,
        member_repo: SubgroupMemberRepository,
        post_repo: PostRepository,
        community_id: uuid.UUID,
        max_memberships_per_user: int = 5,
    ) -> None:
        self._subgroup_repo = subgroup_repo
        self._member_repo = member_repo
        self._post_repo = post_repo
        self._community_id = community_id
        self._max_memberships = max_memberships_per_user
