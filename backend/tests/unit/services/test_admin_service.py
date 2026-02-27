"""
@file test_admin_service.py
@brief Unit tests for AdminService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.admin import (
    CommunityMetrics,
    MetricsResponse,
    SystemMetrics,
    WafMetrics,
)
from app.services.admin_service import AdminService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()


def _make_admin_user() -> MagicMock:
    """@brief Create a mock admin user."""
    user = MagicMock()
    user.id = ADMIN_ID
    user.role = "admin"
    return user


def _make_target_user(role: str = "member", is_active: bool = True) -> MagicMock:
    """@brief Create a mock target user."""
    user = MagicMock()
    user.id = TARGET_ID
    user.role = role
    user.is_active = is_active
    user.deleted_at = None
    return user


def _make_settings() -> MagicMock:
    """@brief Create mock app settings."""
    settings = MagicMock()
    settings.ENABLE_REGISTRATION = True
    settings.REQUIRE_INVITE = False
    settings.STORAGE_QUOTA_DEFAULT = 10737418240
    settings.WAF_ENABLED = True
    settings.APP_VERSION = "0.1.0"
    return settings


class TestGetMetrics:
    """@brief Tests for AdminService.get_metrics()."""

    @pytest.mark.asyncio
    async def test_returns_correct_metric_shape(self):
        """get_metrics should return MetricsResponse with community, system, waf."""
        expected = MetricsResponse(
            community=CommunityMetrics(
                users_total=10,
                users_active_30d=5,
                users_online_now=2,
                posts_total=100,
                posts_last_7d=20,
                media_files=50,
                media_storage_bytes=1024,
            ),
            system=SystemMetrics(
                version="0.1.0",
                uptime_seconds=3600.0,
                db_size_bytes=None,
                valkey_memory_bytes=None,
                celery_queue_depth=0,
            ),
            waf=WafMetrics(blocks_today=0, blocks_by_reason={}),
        )
        with patch(
            "app.services.admin_service.get_metrics_impl",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            service = AdminService(
                session=MagicMock(),
                user_repo=AsyncMock(),
                audit_repo=AsyncMock(),
                community_id=COMMUNITY_ID,
                settings=_make_settings(),
            )
            result = await service.get_metrics()

        assert isinstance(result, MetricsResponse)
        assert result.community.users_total == 10
        assert result.system.version == "0.1.0"
        assert isinstance(result.waf.blocks_by_reason, dict)


class TestChangeRole:
    """@brief Tests for AdminService.change_role()."""

    @pytest.mark.asyncio
    async def test_updates_user_and_logs_audit_entry(self):
        """change_role should update user role and append audit entry."""
        admin = _make_admin_user()
        target = _make_target_user(role="member")
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = target
        mock_user_repo.update = AsyncMock()
        mock_audit_repo = AsyncMock()
        mock_audit_repo.append = AsyncMock()

        service = AdminService(
            session=MagicMock(),
            user_repo=mock_user_repo,
            audit_repo=mock_audit_repo,
            community_id=COMMUNITY_ID,
            settings=_make_settings(),
        )

        await service.change_role(admin, TARGET_ID, "viewer", "127.0.0.1")

        mock_user_repo.update.assert_awaited_once()
        call_args = mock_user_repo.update.call_args
        assert call_args[0][1] == {"role": "viewer"}
        mock_audit_repo.append.assert_awaited_once()
        append_args = mock_audit_repo.append.await_args[1]
        assert append_args["action"] == "admin.user.role_changed"
        assert append_args["target_id"] == TARGET_ID
        assert append_args["extra_data"]["old_role"] == "member"
        assert append_args["extra_data"]["new_role"] == "viewer"

    @pytest.mark.asyncio
    async def test_raises_not_found_when_user_missing(self):
        """change_role should raise NotFoundError when target user not found."""
        admin = _make_admin_user()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = None

        service = AdminService(
            session=MagicMock(),
            user_repo=mock_user_repo,
            audit_repo=AsyncMock(),
            community_id=COMMUNITY_ID,
            settings=_make_settings(),
        )

        with pytest.raises(NotFoundError, match="User not found"):
            await service.change_role(admin, TARGET_ID, "admin", None)


class TestSuspendUser:
    """@brief Tests for AdminService.suspend_user()."""

    @pytest.mark.asyncio
    async def test_sets_is_active_false_and_logs(self):
        """suspend_user should set is_active=False and append audit entry."""
        admin = _make_admin_user()
        target = _make_target_user(is_active=True)
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = target
        mock_user_repo.update = AsyncMock()
        mock_audit_repo = AsyncMock()
        mock_audit_repo.append = AsyncMock()

        service = AdminService(
            session=MagicMock(),
            user_repo=mock_user_repo,
            audit_repo=mock_audit_repo,
            community_id=COMMUNITY_ID,
            settings=_make_settings(),
        )

        await service.suspend_user(admin, TARGET_ID, "192.168.1.1")

        mock_user_repo.update.assert_awaited_once()
        assert mock_user_repo.update.call_args[0][1] == {"is_active": False}
        mock_audit_repo.append.assert_awaited_once()
        assert mock_audit_repo.append.await_args[1]["action"] == "admin.user.suspended"


class TestRestoreUser:
    """@brief Tests for AdminService.restore_user()."""

    @pytest.mark.asyncio
    async def test_clears_deleted_at_and_logs(self):
        """restore_user should clear deleted_at, set is_active=True and log."""
        admin = _make_admin_user()
        target = _make_target_user()
        target.deleted_at = MagicMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id_include_deleted.return_value = target
        mock_user_repo.update = AsyncMock()
        mock_audit_repo = AsyncMock()
        mock_audit_repo.append = AsyncMock()

        service = AdminService(
            session=MagicMock(),
            user_repo=mock_user_repo,
            audit_repo=mock_audit_repo,
            community_id=COMMUNITY_ID,
            settings=_make_settings(),
        )

        await service.restore_user(admin, TARGET_ID, None)

        mock_user_repo.update.assert_awaited_once()
        data = mock_user_repo.update.call_args[0][1]
        assert data["deleted_at"] is None
        assert data["is_active"] is True
        mock_audit_repo.append.assert_awaited_once()
        assert mock_audit_repo.append.await_args[1]["action"] == "admin.user.restored"


class TestListUsers:
    """@brief Tests for AdminService.list_users()."""

    @pytest.mark.asyncio
    async def test_delegates_to_user_repo_with_search(self):
        """list_users should delegate to user_repo.list_by_community_search."""
        mock_users = [_make_target_user()]
        mock_user_repo = AsyncMock()
        mock_user_repo.list_by_community_search.return_value = (mock_users, None)

        service = AdminService(
            session=MagicMock(),
            user_repo=mock_user_repo,
            audit_repo=AsyncMock(),
            community_id=COMMUNITY_ID,
            settings=_make_settings(),
        )

        users, cursor = await service.list_users(search="test", limit=10)

        mock_user_repo.list_by_community_search.assert_awaited_once_with(
            COMMUNITY_ID, search="test", limit=10, cursor=None,
        )
        assert len(users) == 1
        assert cursor is None
