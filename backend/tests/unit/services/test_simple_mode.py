"""
@file test_simple_mode.py
@brief Unit tests: simple_mode user setting + admin toggle (flag guard, audit).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.schemas.settings import UserSettingsUpdate
from app.services.admin_service import AdminService
from app.services.settings_service import SettingsService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
UID = uuid.uuid4()


def _community(enabled: bool) -> MagicMock:
    c = MagicMock()
    c.features = {"simple_mode": enabled}
    return c


def _settings_svc(enabled: bool) -> tuple[SettingsService, AsyncMock]:
    repo = AsyncMock()
    repo.get_or_create.return_value = MagicMock(home_layout=None)
    communities = AsyncMock()
    communities.get.return_value = _community(enabled)
    return SettingsService(repo, AsyncMock(), CID, communities=communities), repo


class TestUserSetting:
    """@brief Self-service toggle."""

    def test_update_schema_accepts_flag(self):
        assert UserSettingsUpdate(simple_mode=True).simple_mode is True

    @pytest.mark.asyncio
    async def test_on_blocked_when_feature_off(self):
        svc, repo = _settings_svc(False)
        with pytest.raises(AppError) as e:
            await svc.update_settings(UID, UserSettingsUpdate(simple_mode=True))
        assert e.value.status_code == 404
        repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_off_allowed_when_feature_off(self):
        svc, repo = _settings_svc(False)
        repo.update.return_value = MagicMock(home_layout=None, simple_mode=False)
        with patch("app.services.settings_service._validate_settings_tolerant"):
            await svc.update_settings(UID, UserSettingsUpdate(simple_mode=False))
        repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_persists_when_feature_on(self):
        svc, repo = _settings_svc(True)
        with patch("app.services.settings_service._validate_settings_tolerant"):
            await svc.update_settings(UID, UserSettingsUpdate(simple_mode=True))
        assert repo.update.await_args.args[1] == {"simple_mode": True}


def _admin_svc(enabled: bool, target: object | None = MagicMock()):
    users = AsyncMock()
    users.get_by_id.return_value = target
    audit = AsyncMock()
    svc = AdminService(AsyncMock(), users, audit, CID, MagicMock())
    return svc, audit


class TestAdminToggle:
    """@brief AdminService.set_simple_mode."""

    @pytest.mark.asyncio
    async def test_sets_and_audits(self):
        svc, audit = _admin_svc(True)
        admin = MagicMock(id=uuid.uuid4())
        with (
            patch("app.services.admin_service.SettingsRepository") as sr,
            patch("app.services.admin_service.CommunityRepository") as cr,
        ):
            cr.return_value.get = AsyncMock(return_value=_community(True))
            sr.return_value.get_or_create = AsyncMock()
            sr.return_value.update = AsyncMock()
            await svc.set_simple_mode(admin, UID, True, "1.2.3.4")
        sr.return_value.update.assert_awaited_once_with(UID, {"simple_mode": True})
        assert audit.append.await_args.kwargs["action"] == "admin.user.simple_mode"

    @pytest.mark.asyncio
    async def test_feature_off_blocks_on(self):
        svc, audit = _admin_svc(False)
        with patch("app.services.admin_service.CommunityRepository") as cr:
            cr.return_value.get = AsyncMock(return_value=_community(False))
            with pytest.raises(AppError):
                await svc.set_simple_mode(MagicMock(), UID, True, None)
        audit.append.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_user_404(self):
        svc, _ = _admin_svc(True, target=None)
        with pytest.raises(NotFoundError):
            await svc.set_simple_mode(MagicMock(), UID, False, None)
