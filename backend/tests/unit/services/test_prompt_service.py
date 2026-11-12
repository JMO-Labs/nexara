"""
@file test_prompt_service.py
@brief Unit tests for PromptService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.post import Post
from app.models.prompt import Prompt, PromptPost
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.schemas.prompt import PromptCreate
from app.services.prompt_service import (
    MAX_PINNED_PROMPTS,
    PromptService,
    should_fire,
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_prompt(
    *,
    frequency_type: str = "weekly",
    is_enabled: bool = True,
    trigger_month: int | None = None,
    trigger_day: int | None = None,
    trigger_weekday: int | None = None,
    trigger_month_day: int | None = None,
    trigger_one_time_date: date | None = None,
    trigger_custom_rule: str | None = None,
    active_days: int = 7,
    generate_summary: bool = True,
    notify_members: bool = False,
) -> MagicMock:
    p = MagicMock(spec=Prompt)
    p.id = uuid.uuid4()
    p.community_id = COMMUNITY_ID
    p.title = "Sample"
    p.body = "Body"
    p.source = "builtin"
    p.is_enabled = is_enabled
    p.frequency_type = frequency_type
    p.trigger_month = trigger_month
    p.trigger_day = trigger_day
    p.trigger_weekday = trigger_weekday
    p.trigger_week_interval = None
    p.trigger_month_day = trigger_month_day
    p.trigger_custom_rule = trigger_custom_rule
    p.trigger_one_time_date = trigger_one_time_date
    p.active_days = active_days
    p.scope = "community"
    p.subgroup_id = None
    p.notify_members = notify_members
    p.notification_body = None
    p.linked_event_id = None
    p.generate_summary = generate_summary
    p.prompt_type = "standard"
    p.interest_category_slug = None
    p.interest_capture_hint = None
    p.created_by = uuid.uuid4()
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


@pytest.fixture
def prompt_repo() -> AsyncMock:
    r = AsyncMock(spec=PromptRepository)
    r.get_post_for_today.return_value = None
    r.count_active_pinned.return_value = 0
    return r


@pytest.fixture
def post_repo() -> AsyncMock:
    r = AsyncMock(spec=PostRepository)

    def _fill_post(p: Post) -> Post:
        p.id = uuid.uuid4()
        p.created_at = datetime.now(UTC)
        return p

    r.create.side_effect = _fill_post
    return r


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(prompt_repo: AsyncMock, post_repo: AsyncMock, session: AsyncMock) -> PromptService:
    return PromptService(
        prompt_repo=prompt_repo,
        post_repo=post_repo,
        community_id=COMMUNITY_ID,
        session=session,
    )


class TestShouldFire:
    def test_disabled_does_not_fire(self) -> None:
        p = _make_prompt(
            is_enabled=False,
            frequency_type="weekly",
            trigger_weekday=date.today().weekday(),
        )
        assert should_fire(p, date.today()) is False

    def test_annual_fires_on_match(self) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="annual_date", trigger_month=4, trigger_day=25)
        assert should_fire(p, today) is True

    def test_annual_skips_off_date(self) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="annual_date", trigger_month=4, trigger_day=24)
        assert should_fire(p, today) is False

    def test_weekly_fires_on_correct_weekday(self) -> None:
        today = date(2026, 4, 25)  # Saturday
        p = _make_prompt(frequency_type="weekly", trigger_weekday=today.weekday())
        assert should_fire(p, today) is True

    def test_weekly_skips_other_days(self) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="weekly", trigger_weekday=(today.weekday() + 1) % 7)
        assert should_fire(p, today) is False

    def test_monthly_fires_on_day(self) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="monthly", trigger_month_day=25)
        assert should_fire(p, today) is True

    def test_one_time_fires_once(self) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="one_time", trigger_one_time_date=today)
        assert should_fire(p, today) is True
        assert should_fire(p, today + timedelta(days=1)) is False


class TestFireDuePrompts:
    @pytest.mark.asyncio
    async def test_fires_matching_prompt(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="weekly", trigger_weekday=today.weekday())
        prompt_repo.list_enabled.return_value = [p]

        def _fill_pp(pp: PromptPost) -> PromptPost:
            pp.id = uuid.uuid4()
            return pp

        prompt_repo.create_prompt_post.side_effect = _fill_pp

        fired = await service.fire_due_prompts(today)
        assert fired == 1
        post_repo.create.assert_awaited_once()
        prompt_repo.create_prompt_post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disabled_does_not_fire(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(
            is_enabled=False,
            frequency_type="weekly",
            trigger_weekday=today.weekday(),
        )
        prompt_repo.list_enabled.return_value = [p]
        fired = await service.fire_due_prompts(today)
        assert fired == 0
        post_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_max_pinned_enforced(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        today = date(2026, 4, 25)
        prompts = [
            _make_prompt(frequency_type="weekly", trigger_weekday=today.weekday())
            for _ in range(MAX_PINNED_PROMPTS + 2)
        ]
        prompt_repo.list_enabled.return_value = prompts
        prompt_repo.count_active_pinned.return_value = 0

        def _fill_pp(pp: PromptPost) -> PromptPost:
            pp.id = uuid.uuid4()
            return pp

        prompt_repo.create_prompt_post.side_effect = _fill_pp

        fired = await service.fire_due_prompts(today)
        assert fired == MAX_PINNED_PROMPTS

    @pytest.mark.asyncio
    async def test_idempotent_for_same_day(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        today = date(2026, 4, 25)
        p = _make_prompt(frequency_type="weekly", trigger_weekday=today.weekday())
        prompt_repo.list_enabled.return_value = [p]
        prompt_repo.get_post_for_today.return_value = MagicMock(spec=PromptPost)

        fired = await service.fire_due_prompts(today)
        assert fired == 0
        post_repo.create.assert_not_awaited()


class TestFinaliseExpired:
    @pytest.mark.asyncio
    async def test_summary_post_created(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        now = datetime.now(UTC)
        prompt = _make_prompt()
        tracker = MagicMock(spec=PromptPost)
        tracker.id = uuid.uuid4()
        tracker.prompt_id = prompt.id
        tracker.post_id = uuid.uuid4()
        tracker.expires_at = now - timedelta(hours=1)
        tracker.response_count = 5
        tracker.is_finalised = False
        tracker.summary_post_id = None

        prompt_repo.list_expired_unfinalised.return_value = [tracker]
        prompt_repo.get_by_id.return_value = prompt

        original = MagicMock(spec=Post)
        original.is_pinned = True
        post_repo.get_by_id.return_value = original

        finalised = await service.finalise_expired(now)
        assert finalised == 1
        post_repo.create.assert_awaited_once()
        prompt_repo.finalise.assert_awaited_once()
        assert original.is_pinned is False

    @pytest.mark.asyncio
    async def test_summary_includes_media_grid(
        self,
        service: PromptService,
        prompt_repo: AsyncMock,
        post_repo: AsyncMock,
    ) -> None:
        now = datetime.now(UTC)
        prompt = _make_prompt()
        tracker = MagicMock(spec=PromptPost)
        tracker.id = uuid.uuid4()
        tracker.prompt_id = prompt.id
        tracker.post_id = uuid.uuid4()
        tracker.expires_at = now - timedelta(hours=1)
        tracker.response_count = 3
        tracker.is_finalised = False
        tracker.summary_post_id = None

        m1, m2, m3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        reply1 = {"id": uuid.uuid4(), "media_ids": [m1, m2]}
        reply2 = {"id": uuid.uuid4(), "media_ids": [m3]}

        prompt_repo.list_expired_unfinalised.return_value = [tracker]
        prompt_repo.get_by_id.return_value = prompt
        post_repo.list_replies_for_prompt.return_value = [reply1, reply2]

        original = MagicMock(spec=Post)
        original.is_pinned = True
        post_repo.get_by_id.return_value = original

        def _fill_post(p: Post) -> Post:
            p.id = uuid.uuid4()
            p.created_at = datetime.now(UTC)
            return p

        post_repo.create.side_effect = _fill_post

        finalised = await service.finalise_expired(now)
        assert finalised == 1
        post_repo.create.assert_awaited_once()
        post_repo.list_replies_for_prompt.assert_awaited_once_with(tracker.prompt_id, limit=50)


class TestCreatePrompt:
    @pytest.mark.asyncio
    async def test_subgroup_scope_requires_subgroup(self, service: PromptService) -> None:
        from app.core.exceptions import AppError

        with pytest.raises(AppError, match="[Ss]ubgroup"):
            await service.create_prompt(
                uuid.uuid4(),
                PromptCreate(
                    title="X",
                    body="b",
                    frequency_type="weekly",
                    trigger_weekday=0,
                    scope="subgroup",
                ),
            )

    @pytest.mark.asyncio
    async def test_create_interest_capture_prompt(
        self, service: PromptService, prompt_repo: AsyncMock
    ) -> None:
        def _fill_prompt(p: Prompt) -> Prompt:
            p.id = uuid.uuid4()
            p.is_enabled = True
            p.created_at = datetime.now(UTC)
            p.updated_at = datetime.now(UTC)
            return p

        prompt_repo.create.side_effect = _fill_prompt
        payload = PromptCreate(
            title="What do you cook?",
            body="Share your favorite cooking experiences",
            prompt_type="interest_capture",
            interest_category_slug="cooking",
            interest_capture_hint="Pick favorite cuisines",
            frequency_type="annual_date",
            trigger_month=12,
            trigger_day=1,
        )
        prompt = await service.create_prompt(uuid.uuid4(), payload)
        assert prompt.prompt_type == "interest_capture"
        assert prompt.interest_category_slug == "cooking"


class TestSeedBuiltinPrompts:
    def test_seed_builtin_prompts_type_distribution(self) -> None:
        """Test that seed includes 15 standard and 9 interest_capture prompts."""
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parents[4] / "backend" / "data" / "builtin_prompts.json"
        data = json.loads(path.read_text(encoding="utf-8"))

        standard_count = sum(
            1 for entry in data if entry.get("prompt_type", "standard") == "standard"
        )
        interest_count = sum(1 for entry in data if entry.get("prompt_type") == "interest_capture")

        assert len(data) == 24
        assert standard_count == 15
        assert interest_count == 9

    def test_seed_builtin_prompts_entry_schema_valid(self) -> None:
        """Test that all 24 entries have valid schema with required fields."""
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parents[4] / "backend" / "data" / "builtin_prompts.json"
        data = json.loads(path.read_text(encoding="utf-8"))

        required_fields = {"title", "body", "frequency_type", "active_days", "scope"}
        for entry in data:
            # Check required fields present
            assert required_fields.issubset(entry.keys()), f"Missing fields in {entry['title']}"
            # Check prompt_type field
            assert entry.get("prompt_type") in [
                "standard",
                "interest_capture",
            ], f"Invalid prompt_type in {entry['title']}"
            # Check interest_capture entries have category slug
            if entry.get("prompt_type") == "interest_capture":
                assert entry.get("interest_category_slug") is not None, (
                    f"interest_category_slug missing in {entry['title']}"
                )
                assert entry.get("interest_capture_hint") is not None, (
                    f"interest_capture_hint missing in {entry['title']}"
                )


def _make_prompt_post(prompt_id: uuid.UUID) -> MagicMock:
    pp = MagicMock(spec=PromptPost)
    pp.id = uuid.uuid4()
    pp.prompt_id = prompt_id
    pp.post_id = uuid.uuid4()
    pp.fired_at = date(2026, 1, 1)
    pp.expires_at = datetime.now(UTC) + timedelta(days=1)
    pp.response_count = 2
    pp.is_finalised = False
    pp.summary_post_id = None
    return pp


class TestPromptPostDetail:
    async def test_list_active_includes_prompt(
        self, service: PromptService, prompt_repo: AsyncMock
    ) -> None:
        prompt = _make_prompt()
        pp = _make_prompt_post(prompt.id)
        prompt_repo.list_active.return_value = [pp]
        prompt_repo.get_by_ids.return_value = [prompt]
        out = await service.list_active()
        assert len(out) == 1
        assert out[0].id == pp.id
        assert out[0].prompt.id == prompt.id
        assert out[0].prompt.title == "Sample"

    async def test_list_active_skips_missing_prompt(
        self, service: PromptService, prompt_repo: AsyncMock
    ) -> None:
        prompt_repo.list_active.return_value = [_make_prompt_post(uuid.uuid4())]
        prompt_repo.get_by_ids.return_value = []
        assert await service.list_active() == []

    async def test_get_prompt_post_detail(
        self, service: PromptService, prompt_repo: AsyncMock
    ) -> None:
        prompt = _make_prompt()
        pp = _make_prompt_post(prompt.id)
        prompt_repo.get_prompt_post.return_value = pp
        prompt_repo.get_by_id.return_value = prompt
        out = await service.get_prompt_post(pp.id)
        assert out.prompt.id == prompt.id
        prompt_repo.get_prompt_post.assert_awaited_once_with(pp.id, community_id=COMMUNITY_ID)

    async def test_get_prompt_post_not_found(
        self, service: PromptService, prompt_repo: AsyncMock
    ) -> None:
        from app.core.exceptions import NotFoundError

        prompt_repo.get_prompt_post.return_value = None
        with pytest.raises(NotFoundError):
            await service.get_prompt_post(uuid.uuid4())
