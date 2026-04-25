"""
@file subgroup.py
@brief Pydantic schemas for subgroups and subgroup membership.

Defines the request and response shapes for the subgroups API:
create / update payloads, detailed subgroup responses, member lists,
role changes, and pinned-post requests.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

#: Valid subgroup roles.
SUBGROUP_ROLES = ("owner", "moderator", "member")

#: Valid join policies.
JOIN_POLICIES = ("open", "invite_only", "admin_approval")


class SubgroupCreate(BaseModel):
    """
    @brief Payload for creating a subgroup.

    @param name Human-readable subgroup name.
    @param slug URL-safe identifier (unique).
    @param description Optional long-form description.
    @param avatar_url Optional avatar URL.
    @param is_private When true, the subgroup is hidden from discovery.
    @param join_policy One of ``open``, ``invite_only``, ``admin_approval``.
    """

    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_private: bool = False
    join_policy: str = Field(default="open", pattern=r"^(open|invite_only|admin_approval)$")


class SubgroupUpdate(BaseModel):
    """
    @brief Partial update payload for an existing subgroup.

    All fields are optional — only supplied fields are applied.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_private: bool | None = None
    join_policy: str | None = Field(default=None, pattern=r"^(open|invite_only|admin_approval)$")


class SubgroupResponse(BaseModel):
    """
    @brief Summary subgroup representation returned from list endpoints.
    """

    id: UUID
    name: str
    slug: str
    description: str | None = None
    avatar_url: str | None = None
    is_private: bool
    join_policy: str
    created_by: UUID | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubgroupDetailResponse(SubgroupResponse):
    """
    @brief Detailed subgroup response including per-viewer state.

    @param member_count Number of active members.
    @param my_role Role of the requesting user (``owner``/``moderator``/
        ``member``) or ``None`` if not a member.
    @param chat_channel_id Auto-created chat channel ID, or ``None``.
    @param pinned_post_id ID of the currently pinned post, if any.
    """

    member_count: int = 0
    my_role: str | None = None
    chat_channel_id: UUID | None = None
    pinned_post_id: UUID | None = None


class MembershipResponse(BaseModel):
    """
    @brief Subgroup member record with embedded user summary.

    @param subgroup_id ID of the subgroup.
    @param user_id ID of the user.
    @param role Member role (``owner``, ``moderator``, ``member``).
    @param invited_by Optional inviter user ID.
    @param joined_at Timestamp the user joined.
    @param username Optional username (populated when enriched).
    @param display_name Optional display name.
    @param avatar_url Optional avatar URL.
    """

    subgroup_id: UUID
    user_id: UUID
    role: str
    invited_by: UUID | None = None
    joined_at: datetime
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class RoleChangeRequest(BaseModel):
    """
    @brief Request payload for changing a member's role.

    @param role Target role — one of ``owner``, ``moderator``, ``member``.
    """

    role: str = Field(pattern=r"^(owner|moderator|member)$")


class PinPostRequest(BaseModel):
    """
    @brief Request payload for pinning a post in a subgroup.

    @param post_id ID of the post to pin (must belong to the subgroup).
    """

    post_id: UUID
