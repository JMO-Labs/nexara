"""
@file test_subgroup_repo.py
@brief Unit tests for SubgroupRepository and SubgroupMemberRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
SUBGROUP_ID = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestSubgroupRepositoryGetBySlug:
    """@brief Tests for SubgroupRepository.get_by_slug()."""

    @pytest.mark.asyncio
    async def test_returns_subgroup_when_found(self):
        """get_by_slug returns the Subgroup when present."""
        session = _make_session()
        sg = MagicMock(spec=Subgroup)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sg
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupRepository(session)
        result = await repo.get_by_slug("family", COMMUNITY_ID)

        assert result is sg
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        """get_by_slug returns None when no match."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupRepository(session)
        result = await repo.get_by_slug("missing", COMMUNITY_ID)

        assert result is None


class TestSubgroupRepositoryCreate:
    """@brief Tests for SubgroupRepository.create_subgroup()."""

    @pytest.mark.asyncio
    async def test_creates_subgroup_with_fields(self):
        """create_subgroup inserts and returns a Subgroup."""
        session = _make_session()
        repo = SubgroupRepository(session)

        result = await repo.create_subgroup(
            community_id=COMMUNITY_ID,
            name="Family",
            slug="family",
            description="desc",
            avatar_url=None,
            is_private=False,
            join_policy="open",
            created_by=USER_ID,
        )

        assert isinstance(result, Subgroup)
        assert result.slug == "family"
        assert result.community_id == COMMUNITY_ID
        assert result.join_policy == "open"
        session.add.assert_called_once()
        session.flush.assert_awaited()


class TestSubgroupRepositoryCreateChannel:
    """@brief Tests for SubgroupRepository.create_chat_channel()."""

    @pytest.mark.asyncio
    async def test_creates_chat_channel(self):
        """create_chat_channel inserts a ChatChannel linked to the subgroup."""
        session = _make_session()
        repo = SubgroupRepository(session)

        result = await repo.create_chat_channel(
            community_id=COMMUNITY_ID,
            subgroup_id=SUBGROUP_ID,
            name="Family",
        )

        assert isinstance(result, ChatChannel)
        assert result.subgroup_id == SUBGROUP_ID
        assert result.channel_type == "subgroup"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


class TestSubgroupRepositoryArchive:
    """@brief Tests for SubgroupRepository.archive()."""

    @pytest.mark.asyncio
    async def test_archive_sets_archived_at(self):
        """archive sets archived_at and flushes."""
        session = _make_session()
        sg = MagicMock(spec=Subgroup)
        sg.archived_at = None
        repo = SubgroupRepository(session)

        result = await repo.archive(sg)

        assert result is sg
        assert sg.archived_at is not None
        session.flush.assert_awaited_once()


class TestSubgroupRepositoryListVisible:
    """@brief Tests for SubgroupRepository.list_visible_for_user()."""

    @pytest.mark.asyncio
    async def test_returns_rows_for_user(self):
        """list_visible_for_user executes and returns rows."""
        session = _make_session()
        sg = MagicMock(spec=Subgroup)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sg]
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupRepository(session)
        rows = await repo.list_visible_for_user(
            COMMUNITY_ID,
            USER_ID,
        )

        assert rows == [sg]
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_query_skips_membership_filter(self):
        """list_visible_for_user with is_admin=True returns all rows."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupRepository(session)
        await repo.list_visible_for_user(
            COMMUNITY_ID,
            USER_ID,
            is_admin=True,
        )

        session.execute.assert_awaited_once()


class TestSubgroupMemberRepositoryAdd:
    """@brief Tests for SubgroupMemberRepository.add_member()."""

    @pytest.mark.asyncio
    async def test_add_member_inserts_row(self):
        """add_member inserts a SubgroupMember row."""
        session = _make_session()
        repo = SubgroupMemberRepository(session)

        result = await repo.add_member(
            community_id=COMMUNITY_ID,
            subgroup_id=SUBGROUP_ID,
            user_id=USER_ID,
            role="owner",
        )

        assert isinstance(result, SubgroupMember)
        assert result.role == "owner"
        assert result.subgroup_id == SUBGROUP_ID
        assert result.user_id == USER_ID
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


class TestSubgroupMemberRepositoryGet:
    """@brief Tests for SubgroupMemberRepository.get_membership()."""

    @pytest.mark.asyncio
    async def test_returns_membership_or_none(self):
        """get_membership returns SubgroupMember when present."""
        session = _make_session()
        membership = MagicMock(spec=SubgroupMember)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = membership
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        assert await repo.get_membership(SUBGROUP_ID, USER_ID) is membership

        mock_result.scalar_one_or_none.return_value = None
        assert await repo.get_membership(SUBGROUP_ID, uuid.uuid4()) is None


class TestSubgroupMemberRepositoryRemove:
    """@brief Tests for SubgroupMemberRepository.remove_member()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self):
        """remove_member returns True when a row is deleted."""
        session = _make_session()
        membership = MagicMock(spec=SubgroupMember)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = membership
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        result = await repo.remove_member(SUBGROUP_ID, USER_ID)

        assert result is True
        session.delete.assert_awaited_once_with(membership)
        session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_returns_false_when_missing(self):
        """remove_member returns False when no membership exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        result = await repo.remove_member(SUBGROUP_ID, USER_ID)

        assert result is False
        session.delete.assert_not_called()


class TestSubgroupMemberRepositoryUpdateRole:
    """@brief Tests for SubgroupMemberRepository.update_role()."""

    @pytest.mark.asyncio
    async def test_update_role_sets_new_value(self):
        """update_role mutates the role attribute and flushes."""
        session = _make_session()
        membership = MagicMock(spec=SubgroupMember)
        membership.role = "member"
        repo = SubgroupMemberRepository(session)

        result = await repo.update_role(membership, "moderator")

        assert result is membership
        assert membership.role == "moderator"
        session.flush.assert_awaited_once()


class TestSubgroupMemberRepositoryCounts:
    """@brief Tests for count helpers."""

    @pytest.mark.asyncio
    async def test_count_for_user_returns_int(self):
        """count_for_user returns the scalar integer result."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        assert await repo.count_for_user(USER_ID, COMMUNITY_ID) == 3

    @pytest.mark.asyncio
    async def test_count_members_returns_int(self):
        """count_members returns the scalar integer result."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 7
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        assert await repo.count_members(SUBGROUP_ID) == 7


class TestSubgroupMemberRepositoryListMembers:
    """@brief Tests for SubgroupMemberRepository.list_members()."""

    @pytest.mark.asyncio
    async def test_list_members_returns_tuples(self):
        """list_members returns (member, user) tuples."""
        session = _make_session()
        m = MagicMock(spec=SubgroupMember)
        u = MagicMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(m, u)]
        session.execute = AsyncMock(return_value=mock_result)

        repo = SubgroupMemberRepository(session)
        rows = await repo.list_members(SUBGROUP_ID)

        assert rows == [(m, u)]


class TestSubgroupRepositoryGetSlugs:
    """@brief Tests for SubgroupRepository.get_slugs()."""

    @pytest.mark.asyncio
    async def test_returns_id_to_slug_map_in_one_query(self):
        """get_slugs maps ids to slugs with a single execute."""
        session = _make_session()
        other = uuid.uuid4()
        result = MagicMock()
        result.all.return_value = [(SUBGROUP_ID, "alpha"), (other, "beta")]
        session.execute.return_value = result

        slugs = await SubgroupRepository(session).get_slugs([SUBGROUP_ID, other], COMMUNITY_ID)

        assert slugs == {SUBGROUP_ID: "alpha", other: "beta"}
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_ids_skips_query(self):
        """get_slugs with no ids returns {} without touching the DB."""
        session = _make_session()
        assert await SubgroupRepository(session).get_slugs([], COMMUNITY_ID) == {}
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_query_is_community_scoped(self):
        """The emitted statement filters on community_id."""
        session = _make_session()
        result = MagicMock()
        result.all.return_value = []
        session.execute.return_value = result

        await SubgroupRepository(session).get_slugs([SUBGROUP_ID], COMMUNITY_ID)

        stmt = session.execute.await_args.args[0]
        compiled = stmt.compile()
        assert "community_id" in str(compiled)
        assert COMMUNITY_ID in compiled.params.values()
