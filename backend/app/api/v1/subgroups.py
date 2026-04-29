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
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.schemas.common import MessageResponse
from app.schemas.subgroup import (
    AddMemberRequest,
    MediaAggregateListResponse,
    MembershipResponse,
    PinPostRequest,
    RoleChangeRequest,
    SubgroupCreate,
    SubgroupDetailResponse,
    SubgroupResponse,
    SubgroupUpdate,
)
from app.services.subgroup_service import SubgroupService
from app.services.subgroups.subgroup_media_service import SubgroupMediaService

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
        cover_media_id=subgroup.cover_media_id,
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
    roles = await service._member_repo.list_my_roles(user.id)  # noqa: SLF001
    out: list[SubgroupResponse] = []
    for s in subgroups:
        resp = SubgroupResponse.model_validate(s)
        resp.my_role = roles.get(s.id)
        out.append(resp)
    return out


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
    """@brief Create a new subgroup. The creator becomes owner unless initial_owner_id is set."""
    subgroup, _channel = await service.create_subgroup(
        user,
        name=body.name,
        slug=body.slug,
        description=body.description,
        avatar_url=body.avatar_url,
        is_private=body.is_private,
        join_policy=body.join_policy,
        parent_id=body.parent_id,
        cover_media_id=body.cover_media_id,
        initial_owner_id=body.initial_owner_id,
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
    raw = body.model_dump(exclude_unset=True)
    # Allow explicit ``parent_id: null`` to detach; strip None for everything else.
    updates = {k: v for k, v in raw.items() if v is not None or k == "parent_id"}
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


@router.delete("/{slug}/permanent", response_model=MessageResponse)
async def hard_delete_subgroup(
    slug: str,
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MessageResponse:
    """@brief Permanently delete a subgroup (community admin only)."""
    await service.hard_delete_subgroup(slug, user)
    return MessageResponse(message=_("Subgroup permanently deleted"))


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


@router.post(
    "/{slug}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    slug: str,
    body: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MembershipResponse:
    """@brief Add a user as a subgroup member (owner or admin only)."""
    membership = await service.add_member(slug, body.user_id, body.role, user)
    # Enrich with user fields so the frontend doesn't render an empty
    # row until the next refetch.
    from sqlalchemy import select as _select

    target = (
        await db.execute(_select(User).where(User.id == membership.user_id))
    ).scalar_one_or_none()
    return MembershipResponse(
        subgroup_id=membership.subgroup_id,
        user_id=membership.user_id,
        role=membership.role,
        invited_by=membership.invited_by,
        joined_at=membership.joined_at,
        username=target.username if target else None,
        display_name=target.display_name if target else None,
        avatar_url=target.avatar_url if target else None,
    )


@router.post("/{slug}/members/{target_user_id}/role", response_model=MembershipResponse)
async def change_member_role(
    slug: str,
    target_user_id: uuid.UUID,
    body: RoleChangeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    service: SubgroupService = Depends(_build_service),
) -> MembershipResponse:
    """@brief Change a member's role (owner or admin only)."""
    membership = await service.change_role(slug, target_user_id, body.role, user)
    from sqlalchemy import select as _select

    target = (
        await db.execute(_select(User).where(User.id == membership.user_id))
    ).scalar_one_or_none()
    return MembershipResponse(
        subgroup_id=membership.subgroup_id,
        user_id=membership.user_id,
        role=membership.role,
        invited_by=membership.invited_by,
        joined_at=membership.joined_at,
        username=target.username if target else None,
        display_name=target.display_name if target else None,
        avatar_url=target.avatar_url if target else None,
    )


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


def _build_media_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SubgroupMediaService:
    """@brief Build SubgroupMediaService with injected repositories."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    return SubgroupMediaService(
        subgroup_repo=SubgroupRepository(db),
        media_repo=SubgroupMediaRepository(db),
        community_id=community_id,
    )


@router.get("/{slug}/media", response_model=MediaAggregateListResponse)
async def list_subgroup_media(
    slug: str,
    source: str = "all",
    cursor: str | None = None,
    limit: int = 60,
    user: User = Depends(get_current_user),
    subgroup_service: SubgroupService = Depends(_build_service),
    media_service: SubgroupMediaService = Depends(_build_media_service),
) -> MediaAggregateListResponse:
    """
    @brief List media aggregated from posts, galleries, and events in a subgroup.

    @param slug Subgroup slug.
    @param source Filter: 'post', 'gallery', 'event', or 'all' (default).
    @param cursor Pagination cursor (timestamp:uuid).
    @param limit Items per page (1-200, default 60).
    @return Media list with pagination.
    """
    # Resolve subgroup from slug
    subgroup = await subgroup_service.get_subgroup(slug, user)

    # Fetch media
    items, next_cursor = await media_service.list_media(
        subgroup_id=subgroup.id,
        viewer_id=user.id,
        source=source,
        cursor=cursor,
        limit=limit,
    )

    return MediaAggregateListResponse(items=items, next_cursor=next_cursor)
