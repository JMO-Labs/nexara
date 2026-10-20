"""
@file test_prompts.py
@brief Integration tests for prompts API: CRUD, firing, responses, summaries, notifications.

Tests prompt operations via HTTP endpoints with mocked external dependencies
(Celery, NotificationService, InterestService).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def _mock_admin() -> MagicMock:
    """@brief Create a mock Admin user."""
    user = MagicMock()
    user.id = ADMIN_ID
    user.community_id = COMMUNITY_ID
    user.is_active = True
    user.role = "admin"
    return user


def _mock_member() -> MagicMock:
    """@brief Create a mock Member user."""
    user = MagicMock()
    user.id = USER_ID
    user.community_id = COMMUNITY_ID
    user.is_active = True
    user.role = "member"
    return user


@pytest.fixture(autouse=True)
def _setup_dependencies(test_app):
    """@brief Inject mock dependencies for all tests."""
    from app.core.dependencies import get_current_user, get_db

    # Default to admin user
    test_app.dependency_overrides[get_current_user] = lambda: _mock_admin()

    # Mock database session
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.delete = AsyncMock()

    test_app.dependency_overrides[get_db] = lambda: mock_db

    yield

    test_app.dependency_overrides.clear()


class TestPromptCreation:
    """@brief Prompt CRUD operations."""

    @pytest.mark.asyncio
    async def test_admin_creates_prompt_201(self, test_app):
        """POST /prompts creates a new prompt (admin only)."""
        from app.models.prompt import Prompt

        prompt_id = uuid.uuid4()
        now = datetime.now(UTC)

        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.id = prompt_id
        mock_prompt.title = "Holiday Memory"
        mock_prompt.body = "Share your favorite holiday memory"
        mock_prompt.frequency_type = "annual_date"
        mock_prompt.trigger_month = 12
        mock_prompt.trigger_day = 25
        mock_prompt.trigger_weekday = None
        mock_prompt.trigger_week_interval = None
        mock_prompt.trigger_month_day = None
        mock_prompt.trigger_custom_rule = None
        mock_prompt.trigger_one_time_date = None
        mock_prompt.is_enabled = True
        mock_prompt.scope = "community"
        mock_prompt.subgroup_id = None
        mock_prompt.prompt_type = "standard"
        mock_prompt.interest_category_slug = None
        mock_prompt.interest_capture_hint = None
        mock_prompt.created_by = ADMIN_ID
        mock_prompt.created_at = now
        mock_prompt.updated_at = now
        mock_prompt.active_days = 7
        mock_prompt.notify_members = True
        mock_prompt.notification_body = None
        mock_prompt.linked_event_id = None
        mock_prompt.generate_summary = True
        mock_prompt.source = "custom"

        with patch(
            "app.repositories.prompt_repo.PromptRepository.create",
            return_value=mock_prompt,
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/prompts",
                    json={
                        "title": "Holiday Memory",
                        "body": "Share your favorite holiday memory",
                        "frequency_type": "annual_date",
                        "trigger_month": 12,
                        "trigger_day": 25,
                    },
                )

            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == str(prompt_id)
            assert data["title"] == "Holiday Memory"

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_prompt_403(self, test_app):
        """Non-admin user cannot create prompts."""
        from app.core.dependencies import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: _mock_member()

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/prompts",
                json={
                    "title": "Holiday Memory",
                    "body": "Share your favorite holiday memory",
                    "frequency_type": "annual_date",
                    "trigger_month": 12,
                    "trigger_day": 25,
                },
            )

        assert resp.status_code == 403


class TestPromptFiring:
    """@brief Prompt firing and pinned post creation."""

    @pytest.mark.asyncio
    async def test_fire_due_prompts_creates_pinned_post(self, test_app):
        """Calling fire_due_prompts directly creates a pinned post and PromptPost tracker."""
        prompt_id = uuid.uuid4()
        post_id = uuid.uuid4()
        today = date(2026, 12, 25)

        mock_prompt = MagicMock()
        mock_prompt.id = prompt_id
        mock_prompt.title = "Holiday Memory"
        mock_prompt.body = "Share your favorite holiday memory"
        mock_prompt.frequency_type = "annual_date"
        mock_prompt.trigger_month = 12
        mock_prompt.trigger_day = 25
        mock_prompt.is_enabled = True
        mock_prompt.created_by = ADMIN_ID
        mock_prompt.active_days = 7
        mock_prompt.notify_members = False
        mock_prompt.prompt_type = "standard"
        mock_prompt.interest_category_slug = None

        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.is_pinned = True
        mock_post.content = "**Holiday Memory**\n\nShare your favorite holiday memory"

        with patch(
            "app.repositories.prompt_repo.PromptRepository.list_enabled",
            return_value=[mock_prompt],
        ):
            with patch(
                "app.repositories.prompt_repo.PromptRepository.count_active_pinned",
                return_value=0,
            ):
                with patch(
                    "app.repositories.prompt_repo.PromptRepository.get_post_for_today",
                    return_value=None,
                ):
                    with patch(
                        "app.repositories.post_repo.PostRepository.create",
                        return_value=mock_post,
                    ):
                        with patch(
                            "app.repositories.prompt_repo.PromptRepository.create_prompt_post",
                        ) as mock_create_pp:
                            from app.repositories.post_repo import PostRepository
                            from app.repositories.prompt_repo import PromptRepository
                            from app.services.prompt_service import PromptService

                            mock_db = AsyncMock()
                            svc = PromptService(
                                prompt_repo=PromptRepository(mock_db),
                                post_repo=PostRepository(mock_db),
                                community_id=COMMUNITY_ID,
                                session=mock_db,
                            )
                            fired = await svc.fire_due_prompts(today)

                            assert fired == 1
                            mock_create_pp.assert_called_once()
                            call_args = mock_create_pp.call_args
                            prompt_post = call_args[0][0]
                            assert prompt_post.prompt_id == prompt_id
                            assert prompt_post.post_id == post_id
                            assert prompt_post.fired_at == today


class TestPromptResponses:
    """@brief Response tracking via reply_to_prompt_id."""

    @pytest.mark.asyncio
    async def test_user_reply_increments_response_count(self, test_app):
        """POST /posts with reply_to_prompt_id increments prompt response_count."""
        from app.models.post import Post
        from app.models.prompt import Prompt

        prompt_id = uuid.uuid4()
        post_id = uuid.uuid4()

        mock_post = MagicMock(spec=Post)
        mock_post.id = post_id
        mock_post.author_id = USER_ID
        mock_post.content = "I love Christmas!"
        mock_post.reply_to_prompt_id = prompt_id

        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.id = prompt_id
        mock_prompt.prompt_type = "standard"
        mock_prompt.interest_category_slug = None

        # Mock the repository method
        with patch(
            "app.repositories.post_repo.PostRepository.create_post",
            return_value=mock_post,
        ):
            with patch(
                "app.repositories.post_repo.PostRepository.get_post_detail",
                return_value={
                    "id": str(post_id),
                    "content": "I love Christmas!",
                    "author_id": str(USER_ID),
                    "reply_to_prompt_id": str(prompt_id),
                },
            ):
                with patch(
                    "app.repositories.prompt_repo.PromptRepository.increment_response_count",
                ) as mock_incr:
                    with patch(
                        "app.repositories.prompt_repo.PromptRepository.get_by_id",
                        return_value=mock_prompt,
                    ):
                        from app.repositories.comment_repo import (
                            CommentRepository,
                            ReactionRepository,
                        )
                        from app.repositories.post_repo import PostRepository
                        from app.repositories.prompt_repo import PromptRepository
                        from app.services.notification_service import NotificationService
                        from app.services.post_service import PostService

                        mock_db = AsyncMock()
                        notif_svc = NotificationService(
                            notification_repo=MagicMock(),
                            settings_repo=MagicMock(),
                            community_id=COMMUNITY_ID,
                        )
                        svc = PostService(
                            post_repo=PostRepository(mock_db),
                            comment_repo=CommentRepository(mock_db),
                            reaction_repo=ReactionRepository(mock_db),
                            notification_service=notif_svc,
                            community_id=COMMUNITY_ID,
                            prompt_repo=PromptRepository(mock_db),
                        )

                        user = _mock_member()
                        await svc.create_post(
                            user, "I love Christmas!", reply_to_prompt_id=prompt_id
                        )

                        mock_incr.assert_called_once_with(prompt_id)


class TestPromptExpiry:
    """@brief Summary generation on expiry."""

    @pytest.mark.asyncio
    async def test_finalise_expired_creates_summary_with_media_ids(self, test_app):
        """finalise_expired generates a summary post with media_ids from replies."""
        prompt_id = uuid.uuid4()
        post_id = uuid.uuid4()
        summary_post_id = uuid.uuid4()
        media_id_1 = uuid.uuid4()
        media_id_2 = uuid.uuid4()

        mock_prompt = MagicMock()
        mock_prompt.id = prompt_id
        mock_prompt.title = "Holiday Memory"
        mock_prompt.created_by = ADMIN_ID
        mock_prompt.generate_summary = True
        mock_prompt.prompt_type = "standard"
        mock_prompt.interest_category_slug = None

        mock_tracker = MagicMock()
        mock_tracker.prompt_id = prompt_id
        mock_tracker.post_id = post_id
        mock_tracker.response_count = 2
        mock_tracker.is_finalised = False

        # Mock replies with media
        mock_replies = [
            MagicMock(media_ids=[media_id_1, media_id_2]),
            MagicMock(media_ids=[]),
        ]

        mock_summary = MagicMock()
        mock_summary.id = summary_post_id

        mock_original = MagicMock()
        mock_original.is_pinned = True

        now = datetime.now(UTC) + timedelta(days=8)

        with patch(
            "app.repositories.prompt_repo.PromptRepository.list_expired_unfinalised",
            return_value=[mock_tracker],
        ):
            with patch(
                "app.repositories.prompt_repo.PromptRepository.get_by_id",
                return_value=mock_prompt,
            ):
                with patch(
                    "app.repositories.post_repo.PostRepository.list_replies_for_prompt",
                    return_value=mock_replies,
                ):
                    with patch(
                        "app.repositories.post_repo.PostRepository.create",
                        return_value=mock_summary,
                    ):
                        with patch(
                            "app.repositories.post_repo.PostRepository.get_by_id",
                            return_value=mock_original,
                        ):
                            with patch(
                                "app.repositories.prompt_repo.PromptRepository.finalise",
                            ) as mock_finalise:
                                from app.repositories.post_repo import PostRepository
                                from app.repositories.prompt_repo import PromptRepository
                                from app.services.prompt_service import PromptService

                                mock_db = AsyncMock()
                                svc = PromptService(
                                    prompt_repo=PromptRepository(mock_db),
                                    post_repo=PostRepository(mock_db),
                                    community_id=COMMUNITY_ID,
                                    session=mock_db,
                                )

                                finalised = await svc.finalise_expired(now)

                                assert finalised == 1
                                mock_finalise.assert_called_once()
                                # Verify summary was created
                                call_args = mock_finalise.call_args
                                assert call_args[0][0] == mock_tracker
                                assert call_args[0][1] == summary_post_id


class TestPromptNotifications:
    """@brief Notification delivery on firing and expiry."""

    @pytest.mark.asyncio
    async def test_fire_prompts_notifies_subscribers(self, test_app):
        """fire_due_prompts sends notification when notify_members=True."""
        prompt_id = uuid.uuid4()
        post_id = uuid.uuid4()
        today = date(2026, 12, 25)

        mock_prompt = MagicMock()
        mock_prompt.id = prompt_id
        mock_prompt.title = "Holiday Memory"
        mock_prompt.body = "Share your favorite holiday memory"
        mock_prompt.frequency_type = "annual_date"
        mock_prompt.trigger_month = 12
        mock_prompt.trigger_day = 25
        mock_prompt.is_enabled = True
        mock_prompt.created_by = ADMIN_ID
        mock_prompt.active_days = 7
        mock_prompt.notify_members = True
        mock_prompt.notification_body = "Don't forget to share!"
        mock_prompt.prompt_type = "standard"
        mock_prompt.interest_category_slug = None

        mock_post = MagicMock()
        mock_post.id = post_id

        mock_notif = AsyncMock()

        with patch(
            "app.repositories.prompt_repo.PromptRepository.list_enabled",
            return_value=[mock_prompt],
        ):
            with patch(
                "app.repositories.prompt_repo.PromptRepository.count_active_pinned",
                return_value=0,
            ):
                with patch(
                    "app.repositories.prompt_repo.PromptRepository.get_post_for_today",
                    return_value=None,
                ):
                    with patch(
                        "app.repositories.post_repo.PostRepository.create",
                        return_value=mock_post,
                    ):
                        with patch(
                            "app.repositories.prompt_repo.PromptRepository.create_prompt_post",
                        ):
                            from app.repositories.post_repo import PostRepository
                            from app.repositories.prompt_repo import PromptRepository
                            from app.services.prompt_service import PromptService

                            mock_db = AsyncMock()
                            svc = PromptService(
                                prompt_repo=PromptRepository(mock_db),
                                post_repo=PostRepository(mock_db),
                                community_id=COMMUNITY_ID,
                                session=mock_db,
                                notification_service=mock_notif,
                            )

                            await svc.fire_due_prompts(today)

                            mock_notif.notify.assert_called_once()
                            call_args = mock_notif.notify.call_args
                            assert call_args[1]["type"] == "prompt"
                            assert call_args[1]["payload"]["prompt_id"] == str(prompt_id)


class TestInterestCapture:
    """@brief Interest capture and suggestions."""

    @pytest.mark.asyncio
    async def test_interest_capture_prompt_reply_suggests_interest(self, test_app):
        """Replying to interest_capture prompt triggers interest suggestion."""
        from app.models.prompt import Prompt

        prompt_id = uuid.uuid4()
        post_id = uuid.uuid4()

        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.author_id = USER_ID
        mock_post.content = "I love Thai and Italian food!"
        mock_post.reply_to_prompt_id = prompt_id

        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.id = prompt_id
        mock_prompt.prompt_type = "interest_capture"
        mock_prompt.interest_category_slug = "cooking"
        mock_prompt.interest_capture_hint = "Pick favorite cuisines"

        mock_interest_svc = AsyncMock()

        with patch(
            "app.repositories.post_repo.PostRepository.create_post",
            return_value=mock_post,
        ):
            with patch(
                "app.repositories.post_repo.PostRepository.get_post_detail",
                return_value={
                    "id": str(post_id),
                    "content": "I love Thai and Italian food!",
                    "author_id": str(USER_ID),
                },
            ):
                with patch(
                    "app.repositories.prompt_repo.PromptRepository.increment_response_count",
                ):
                    with patch(
                        "app.repositories.prompt_repo.PromptRepository.get_by_id",
                        return_value=mock_prompt,
                    ):
                        from app.repositories.comment_repo import (
                            CommentRepository,
                            ReactionRepository,
                        )
                        from app.repositories.post_repo import PostRepository
                        from app.repositories.prompt_repo import PromptRepository
                        from app.services.notification_service import NotificationService
                        from app.services.post_service import PostService

                        mock_db = AsyncMock()
                        notif_svc = NotificationService(
                            notification_repo=MagicMock(),
                            settings_repo=MagicMock(),
                            community_id=COMMUNITY_ID,
                        )

                        # Create service with mock interest_service
                        svc = PostService(
                            post_repo=PostRepository(mock_db),
                            comment_repo=CommentRepository(mock_db),
                            reaction_repo=ReactionRepository(mock_db),
                            notification_service=notif_svc,
                            community_id=COMMUNITY_ID,
                            prompt_repo=PromptRepository(mock_db),
                            interest_service=mock_interest_svc,
                        )

                        user = _mock_member()
                        await svc.create_post(
                            user,
                            "I love Thai and Italian food!",
                            reply_to_prompt_id=prompt_id,
                        )

                        # Verify the interest service suggestion was called
                        mock_interest_svc.suggest_for_user.assert_called_once_with(
                            USER_ID, "cooking", "I love Thai and Italian food!"
                        )
