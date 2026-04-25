"""
@file test_subgroup_service.py
@brief Unit tests for SubgroupService covering the six plan cases.

The six cases from the Phase 2 plan are:
  1. Create subgroup with valid data
  2. Creator becomes owner
  3. Chat channel auto-created
  4. Join with open policy succeeds
  5. Join with invite-only policy creates pending request
  6. Membership limit enforced
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConflictError
from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.services.subgroup_service import SubgroupService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_user(
    *,
    role: str = "member",
    user_id: uuid.UUID | None = None,
) -> MagicMock:
    """@brief Build a mock User with the requested role."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.display_name = "Alice"
    user.username = "alice"
    user.avatar_url = None
    return user


def _make_subgroup(
    *,
    slug: str = "family",
    is_private: bool = False,
    join_policy: str = "open",
    archived: bool = False,
    created_by: uuid.UUID | None = None,
) -> MagicMock:
    """@brief Build a mock Subgroup ORM row."""
    sg = MagicMock(spec=Subgroup)
    sg.id = uuid.uuid4()
    sg.community_id = COMMUNITY_ID
    sg.name = "Family"
    sg.slug = slug
    sg.description = None
    sg.avatar_url = None
    sg.is_private = is_private
    sg.join_policy = join_policy
    sg.created_by = created_by or uuid.uuid4()
    sg.archived_at = datetime.now(UTC) if archived else None
    sg.created_at = datetime.now(UTC)
    sg.updated_at = datetime.now(UTC)
    return sg


@pytest.fixture
def subgroup_repo() -> AsyncMock:
    return AsyncMock(spec=SubgroupRepository)


@pytest.fixture
def member_repo() -> AsyncMock:
    return AsyncMock(spec=SubgroupMemberRepository)


@pytest.fixture
def post_repo() -> AsyncMock:
    return AsyncMock(spec=PostRepository)


@pytest.fixture
def service(subgroup_repo, member_repo, post_repo) -> SubgroupService:
    return SubgroupService(
        subgroup_repo=subgroup_repo,
        member_repo=member_repo,
        post_repo=post_repo,
        community_id=COMMUNITY_ID,
        max_memberships_per_user=5,
    )


class TestCreateSubgroup:
    """@brief Cases 1, 2, and 3 from the plan."""

    @pytest.mark.asyncio
    async def test_creates_subgroup_with_valid_data(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 1 — creates with valid data and returns the row."""
        user = _make_user()
        subgroup_repo.get_by_slug.return_value = None
        created = _make_subgroup(slug="family")
        subgroup_repo.create_subgroup.return_value = created
        channel = MagicMock(spec=ChatChannel)
        subgroup_repo.create_chat_channel.return_value = channel

        subgroup, chat = await service.create_subgroup(
            user,
            name="Family",
            slug="family",
            description="Family branch",
            is_private=False,
            join_policy="open",
        )

        assert subgroup is created
        assert chat is channel
        subgroup_repo.create_subgroup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creator_becomes_owner(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 2 — creator auto-added as owner."""
        user = _make_user()
        subgroup_repo.get_by_slug.return_value = None
        created = _make_subgroup()
        subgroup_repo.create_subgroup.return_value = created
        subgroup_repo.create_chat_channel.return_value = MagicMock(spec=ChatChannel)

        await service.create_subgroup(
            user,
            name="Family",
            slug="family",
        )

        member_repo.add_member.assert_awaited_once()
        kwargs = member_repo.add_member.await_args.kwargs
        assert kwargs["role"] == "owner"
        assert kwargs["user_id"] == user.id
        assert kwargs["subgroup_id"] == created.id

    @pytest.mark.asyncio
    async def test_chat_channel_auto_created(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 3 — chat channel row is inserted on creation."""
        user = _make_user()
        subgroup_repo.get_by_slug.return_value = None
        created = _make_subgroup(slug="trip-italy")
        subgroup_repo.create_subgroup.return_value = created
        channel = MagicMock(spec=ChatChannel)
        subgroup_repo.create_chat_channel.return_value = channel

        _, chat = await service.create_subgroup(
            user,
            name="Trip Italy",
            slug="trip-italy",
        )

        subgroup_repo.create_chat_channel.assert_awaited_once()
        kwargs = subgroup_repo.create_chat_channel.await_args.kwargs
        assert kwargs["subgroup_id"] == created.id
        assert kwargs["community_id"] == COMMUNITY_ID
        assert chat is channel

    @pytest.mark.asyncio
    async def test_duplicate_slug_rejected(
        self,
        service,
        subgroup_repo,
    ):
        """Sanity — duplicate slug raises ConflictError."""
        user = _make_user()
        subgroup_repo.get_by_slug.return_value = _make_subgroup(slug="family")

        with pytest.raises(ConflictError):
            await service.create_subgroup(user, name="Family", slug="family")


class TestJoinSubgroup:
    """@brief Cases 4, 5, and 6 from the plan."""

    @pytest.mark.asyncio
    async def test_join_with_open_policy_succeeds(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 4 — open policy adds membership immediately."""
        user = _make_user()
        subgroup = _make_subgroup(slug="family", join_policy="open")
        subgroup_repo.get_by_slug.return_value = subgroup
        member_repo.get_membership.return_value = None
        member_repo.count_for_user.return_value = 0

        result = await service.join_subgroup("family", user)

        assert result["status"] == "joined"
        assert result["role"] == "member"
        member_repo.add_member.assert_awaited_once()
        kwargs = member_repo.add_member.await_args.kwargs
        assert kwargs["role"] == "member"
        assert kwargs["user_id"] == user.id

    @pytest.mark.asyncio
    async def test_join_with_invite_only_creates_pending_request(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 5 — invite-only policy returns pending status without adding."""
        user = _make_user()
        subgroup = _make_subgroup(slug="vip", join_policy="invite_only")
        subgroup_repo.get_by_slug.return_value = subgroup
        member_repo.get_membership.return_value = None
        member_repo.count_for_user.return_value = 0

        result = await service.join_subgroup("vip", user)

        assert result["status"] == "pending"
        assert result["policy"] == "invite_only"
        member_repo.add_member.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_membership_limit_enforced(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Case 6 — exceeding max memberships raises ConflictError."""
        user = _make_user()
        subgroup = _make_subgroup(slug="family", join_policy="open")
        subgroup_repo.get_by_slug.return_value = subgroup
        member_repo.get_membership.return_value = None
        member_repo.count_for_user.return_value = 5  # at cap

        with pytest.raises(ConflictError):
            await service.join_subgroup("family", user)

        member_repo.add_member.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_admin_bypasses_membership_limit(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Admin bypass — admins ignore the per-user cap."""
        admin = _make_user(role="admin")
        subgroup = _make_subgroup(slug="family", join_policy="open")
        subgroup_repo.get_by_slug.return_value = subgroup
        member_repo.get_membership.return_value = None
        member_repo.count_for_user.return_value = 999

        result = await service.join_subgroup("family", admin)

        assert result["status"] == "joined"
        member_repo.add_member.assert_awaited_once()


class TestAdminVisibility:
    """@brief Admin oversight — private subgroups visible to admins."""

    @pytest.mark.asyncio
    async def test_admin_can_view_private_subgroup(
        self,
        service,
        subgroup_repo,
        member_repo,
    ):
        """Admin bypass — private subgroups are visible even without membership."""
        admin = _make_user(role="admin")
        subgroup = _make_subgroup(slug="secret", is_private=True)
        subgroup_repo.get_by_slug.return_value = subgroup

        result = await service.get_subgroup("secret", admin)

        assert result is subgroup
        # Admin path should NOT consult membership for visibility.
        member_repo.get_membership.assert_not_awaited()


class TestPinPost:
    """@brief Pinning an announcement post clears previous pin."""

    @pytest.mark.asyncio
    async def test_pin_post_unsets_previous_pin(
        self,
        service,
        subgroup_repo,
        member_repo,
        post_repo,
    ):
        """Pinning a post clears the existing pin in the same subgroup."""
        owner = _make_user()
        subgroup = _make_subgroup(slug="family")
        subgroup_repo.get_by_slug.return_value = subgroup

        # Owner membership so role check passes.
        owner_membership = MagicMock(spec=SubgroupMember)
        owner_membership.role = "owner"
        member_repo.get_membership.return_value = owner_membership

        post_id = uuid.uuid4()
        post = MagicMock()
        post.id = post_id
        post.subgroup_id = subgroup.id
        post.is_pinned = False
        post_repo.get_by_id.return_value = post

        # post_repo._session has an execute AsyncMock so the UPDATE runs.
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        post_repo._session = session

        result = await service.pin_post("family", post_id, owner)

        assert result["post_id"] == str(post_id)
        assert post.is_pinned is True
        # One UPDATE was issued to clear prior pins.
        session.execute.assert_awaited()
