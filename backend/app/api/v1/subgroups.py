"""
@file subgroups.py
@brief Subgroups API — CRUD, membership, role, and pinned-post endpoints.

All endpoints require authentication. Community admins bypass
membership and role checks as enforced by
:class:`app.services.subgroup_service.SubgroupService`.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.schemas.common import MessageResponse
from app.schemas.subgroup import (
    MembershipResponse,
    PinPostRequest,
    RoleChangeRequest,
    SubgroupCreate,
    SubgroupDetailResponse,
    SubgroupResponse,
    SubgroupUpdate,
)
from app.services.subgroup_service import SubgroupService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/subgroups", tags=["subgroups"])


def _build_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SubgroupService:
    """@brief Build SubgroupService with injected repositories."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    return SubgroupService(
        subgroup_repo=SubgroupRepository(db),
        member_repo=SubgroupMemberRepository(db),
        post_repo=PostRepository(db),
        community_id=community_id,
        max_memberships_per_user=settings.MAX_SUBGROUP_MEMBERSHIPS_PER_USER,
    )


async def _detail_response(
    service: SubgroupService,
    subgroup: Any,
    user: User,
) -> SubgroupDetailResponse:
    """@brief Assemble a SubgroupDetailResponse with per-viewer fields."""
    member_count = await service._member_repo.count_members(subgroup.id)  # noqa: SLF001
    membership = await service._member_repo.get_membership(  # noqa: SLF001
        subgroup.id, user.id
    )
    channel = await service._subgroup_repo.get_chat_channel(subgroup.id)  # noqa: SLF001
    pinned_post_id = await service.get_pinned_post_id(subgroup.id)

    return SubgroupDetailResponse(
        id=subgroup.id,
        name=subgroup.name,
        slug=subgroup.slug,
        description=subgroup.description,
        avatar_url=subgroup.avatar_url,
        is_private=subgroup.is_private,
        join_policy=subgroup.join_policy,
        created_by=subgroup.created_by,
        archived_at=subgroup.archived_at,
        created_at=subgroup.created_at,
        updated_at=subgroup.updated_at,
        member_count=member_count,
        my_role=membership.role if membership else None,
        chat_channel_id=channel.id if channel else None,
        pinned_post_id=pinned_post_id,
    )


@router.get("", response_model=list[SubgroupResponse])
async def list_subgroups(
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> list[SubgroupResponse]:
    """@brief List subgroups visible to the current user."""
    subgroups = await service.list_subgroups(user)
    return [SubgroupResponse.model_validate(s) for s in subgroups]


@router.post(
    "",
    response_model=SubgroupDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subgroup(
    body: SubgroupCreate,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> SubgroupDetailResponse:
    """@brief Create a new subgroup. The creator becomes owner."""
    subgroup, _channel = await service.create_subgroup(
        user,
        name=body.name,
        slug=body.slug,
        description=body.description,
        avatar_url=body.avatar_url,
        is_private=body.is_private,
        join_policy=body.join_policy,
    )
    return await _detail_response(service, subgroup, user)


@router.get("/{slug}", response_model=SubgroupDetailResponse)
async def get_subgroup(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> SubgroupDetailResponse:
    """@brief Fetch a subgroup by slug."""
    subgroup = await service.get_subgroup(slug, user)
    return await _detail_response(service, subgroup, user)


@router.put("/{slug}", response_model=SubgroupDetailResponse)
async def update_subgroup(
    slug: str,
    body: SubgroupUpdate,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> SubgroupDetailResponse:
    """@brief Update a subgroup (owner/moderator/admin only)."""
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    subgroup = await service.update_subgroup(slug, user, updates)
    return await _detail_response(service, subgroup, user)


@router.delete("/{slug}", response_model=MessageResponse)
async def archive_subgroup(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MessageResponse:
    """@brief Archive a subgroup (owner or admin only)."""
    await service.archive_subgroup(slug, user)
    return MessageResponse(message=_("Subgroup archived"))


@router.post("/{slug}/join")
async def join_subgroup(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Join a subgroup (or request access, per join policy)."""
    return await service.join_subgroup(slug, user)


@router.post("/{slug}/leave", response_model=MessageResponse)
async def leave_subgroup(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MessageResponse:
    """@brief Leave a subgroup."""
    await service.leave_subgroup(slug, user)
    return MessageResponse(message=_("Left subgroup"))


@router.get("/{slug}/members", response_model=list[MembershipResponse])
async def list_members(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> list[MembershipResponse]:
    """@brief List members of a subgroup."""
    rows = await service.list_members(slug, user)
    return [
        MembershipResponse(
            subgroup_id=m.subgroup_id,
            user_id=m.user_id,
            role=m.role,
            invited_by=m.invited_by,
            joined_at=m.joined_at,
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
        )
        for m, u in rows
    ]


@router.post("/{slug}/members/{target_user_id}/role", response_model=MembershipResponse)
async def change_member_role(
    slug: str,
    target_user_id: uuid.UUID,
    body: RoleChangeRequest,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MembershipResponse:
    """@brief Change a member's role (owner or admin only)."""
    membership = await service.change_role(slug, target_user_id, body.role, user)
    return MembershipResponse.model_validate(membership)


@router.delete("/{slug}/members/{target_user_id}", response_model=MessageResponse)
async def remove_member(
    slug: str,
    target_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MessageResponse:
    """@brief Remove a member from a subgroup (owner/moderator/admin)."""
    await service.remove_member(slug, target_user_id, user)
    return MessageResponse(message=_("Member removed"))


@router.post("/{slug}/pinned-post")
async def pin_post(
    slug: str,
    body: PinPostRequest,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Pin a post as the subgroup announcement."""
    return await service.pin_post(slug, body.post_id, user)


@router.delete("/{slug}/pinned-post", response_model=MessageResponse)
async def unpin_post(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MessageResponse:
    """@brief Remove the pinned post from a subgroup."""
    await service.unpin_post(slug, user)
    return MessageResponse(message=_("Pinned post cleared"))
