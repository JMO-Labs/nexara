"""
@file test_calendar_service.py
@brief Unit tests for CalendarService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.calendar import Calendar
from app.repositories.calendar_repo import CalendarRepository
from app.services.calendar_service import CalendarService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_cal(
    *,
    kind: str,
    name: str = "X",
    owner_id: uuid.UUID | None = None,
    subgroup_id: uuid.UUID | None = None,
) -> MagicMock:
    cal = MagicMock(spec=Calendar)
    cal.id = uuid.uuid4()
    cal.community_id = COMMUNITY_ID
    cal.kind = kind
    cal.name = name
    cal.owner_id = owner_id
    cal.subgroup_id = subgroup_id
    cal.color = None
    cal.external_provider = None
    cal.external_id = None
    cal.created_at = datetime.now(UTC)
    return cal


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=CalendarRepository)


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repo: AsyncMock, session: AsyncMock) -> CalendarService:
    return CalendarService(
        calendar_repo=repo,
        community_id=COMMUNITY_ID,
        session=session,
    )


class TestListForUser:
    @pytest.mark.asyncio
    async def test_returns_repo_results(
        self, service: CalendarService, repo: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        community = _make_cal(kind="community", name="Community")
        personal = _make_cal(kind="personal", name="Personal", owner_id=user_id)
        repo.list_for_user.return_value = [community, personal]
        out = await service.list_for_user(user_id)
        assert len(out) == 2
        kinds = {c.kind for c in out}
        assert kinds == {"community", "personal"}


class TestDeriveCalendarId:
    @pytest.mark.asyncio
    async def test_private_uses_personal(
        self, service: CalendarService, repo: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        cal = _make_cal(kind="personal", owner_id=user_id)
        repo.ensure_personal.return_value = cal
        out = await service.derive_calendar_id(
            user_id=user_id, visibility="private", subgroup_id=None
        )
        assert out == cal.id
        repo.ensure_personal.assert_awaited_once_with(COMMUNITY_ID, user_id)

    @pytest.mark.asyncio
    async def test_subgroup_uses_subgroup_calendar(
        self, service: CalendarService, repo: AsyncMock
    ) -> None:
        sg_id = uuid.uuid4()
        cal = _make_cal(kind="subgroup", subgroup_id=sg_id)
        repo.get_for_subgroup.return_value = cal
        out = await service.derive_calendar_id(
            user_id=uuid.uuid4(), visibility="subgroup", subgroup_id=sg_id
        )
        assert out == cal.id

    @pytest.mark.asyncio
    async def test_community_default(
        self, service: CalendarService, repo: AsyncMock
    ) -> None:
        cal = _make_cal(kind="community")
        repo.ensure_community.return_value = cal
        out = await service.derive_calendar_id(
            user_id=uuid.uuid4(), visibility="community", subgroup_id=None
        )
        assert out == cal.id
