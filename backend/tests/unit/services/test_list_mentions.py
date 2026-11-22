"""
@file test_list_mentions.py
@brief Tests for mention tagging in list creation and updates.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.list import List
from app.services.list_service import ListService

COMMUNITY_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
LIST_ID = uuid.uuid4()


@pytest.fixture
def repo_list():
    """@brief Mock ListRepository."""
    return AsyncMock()


@pytest.fixture
def repo_member():
    """@brief Mock ListMemberRepository."""
    return AsyncMock()


@pytest.fixture
def tag_repo():
    """@brief Mock TagRepository."""
    return AsyncMock()


@pytest.fixture
def session():
    """@brief Mock AsyncSession."""
    session = AsyncMock()
    # Make execute() return a mock that supports async iteration
    exec_result = AsyncMock()
    exec_result.scalar_one_or_none.return_value = MagicMock(id=OWNER_ID, display_name="List Owner")
    session.execute.return_value = exec_result
    return session


@pytest.fixture
def service(repo_list, repo_member, session, tag_repo):
    """@brief ListService instance with mocked repos."""
    from app.services.list_field_registry import ListFieldRegistry

    return ListService(
        repo_list=repo_list,
        repo_member=repo_member,
        field_registry=ListFieldRegistry(),
        community_id=COMMUNITY_ID,
        session=session,
        notification_service=AsyncMock(),
        tag_repo=tag_repo,
    )


class TestListMentionTagging:
    """@brief Tests for mention tagging in lists."""

    @pytest.mark.asyncio
    async def test_create_list_syncs_mentions_in_description(self, service, repo_list, tag_repo):
        """create() syncs mentions when description contains @mentions."""
        lst = List(
            id=LIST_ID,
            community_id=COMMUNITY_ID,
            owner_id=OWNER_ID,
            title="My List",
            description="Check with @alice and @bob",
            visibility="community",
            status="active",
            field_schema=[],
            item_count=0,
            completed_count=0,
            signup_count=0,
        )
        repo_list.create.return_value = lst

        result = await service.create(
            OWNER_ID,
            title="My List",
            visibility="community",
            description="Check with @alice and @bob",
        )

        assert result.id == LIST_ID
        tag_repo.users_by_username.assert_called_once()
        # Verify sync_mentions was called (via tag_repo)
        args = tag_repo.users_by_username.await_args.args
        assert args[0] == COMMUNITY_ID

    @pytest.mark.asyncio
    async def test_update_list_syncs_mentions_in_description(
        self, service, repo_list, repo_member, tag_repo
    ):
        """update() syncs mentions when description is changed."""
        lst = List(
            id=LIST_ID,
            community_id=COMMUNITY_ID,
            owner_id=OWNER_ID,
            title="My List",
            description="Updated @charlie",
            visibility="community",
            status="active",
            field_schema=[],
            item_count=0,
            completed_count=0,
            signup_count=0,
        )
        repo_list.get_by_id.return_value = lst
        repo_member.get_member.return_value = None
        repo_list.update.return_value = lst

        result = await service.update(LIST_ID, OWNER_ID, {"description": "Updated @charlie"})

        assert result.id == LIST_ID
        tag_repo.users_by_username.assert_called_once()
