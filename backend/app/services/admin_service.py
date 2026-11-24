"""
@file admin_service.py
@brief Admin panel business logic: user management, settings.

Handles role changes, suspension/restore, and admin settings.
Metrics aggregation is delegated to admin_metrics module.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.features import require_feature
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.two_factor_repo import TwoFactorRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import (
    AdminSettingsResponse,
    AdminSettingsUpdate,
    MetricsResponse,
)
from app.services.admin_metrics import get_metrics as get_metrics_impl

logger = structlog.get_logger(__name__)


class AdminService:
    """
    @brief Stateless service for admin panel operations.

    @param session Async DB session.
    @param user_repo User repository.
    @param audit_repo Audit log repository.
    @param community_id Community scope.
    @param settings Application config.
    """

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        audit_repo: AuditRepository,
        community_id: uuid.UUID,
        settings: Settings,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._community_id = community_id
        self._settings = settings

    async def get_metrics(self) -> MetricsResponse:
        """
        @brief Aggregate community, system, and WAF metrics.

        Delegates to admin_metrics.get_metrics.
        @return Combined MetricsResponse.
        """
        return await get_metrics_impl(
            self._session,
            self._user_repo,
            self._community_id,
            self._settings,
        )

    async def change_role(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        new_role: str,
        ip: str | None,
    ) -> None:
        """
        @brief Update a user's role and log the action.

        @param admin_user The admin performing the action.
        @param target_user_id UUID of the user to update.
        @param new_role New role (admin, member, viewer).
        @param ip IP address of the request.
        @raises NotFoundError If the target user is not found.
        """
        target = await self._user_repo.get_by_id(target_user_id, self._community_id)
        if not target:
            raise NotFoundError(message=_("User not found"))
        old_role = target.role
        fields: dict[str, Any] = {"role": new_role}
        if (old_role == "admin") != (new_role == "admin"):
            policy = await TwoFactorRepository(self._session).get_policy(self._community_id)
            if policy == "admins":
                # Coverage flips: drop any stale clock; the next token mint starts a fresh one.
                fields["two_factor_required_since"] = None
        await self._user_repo.update(target, fields)
        await self._audit_repo.append(
            actor_id=admin_user.id,
            action="admin.user.role_changed",
            target_type="user",
            target_id=target_user_id,
            extra_data={"old_role": old_role, "new_role": new_role},
            ip_address=ip,
        )
        logger.info(
            "admin_role_changed",
            admin_id=str(admin_user.id),
            target_id=str(target_user_id),
            new_role=new_role,
        )

    async def set_simple_mode(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        value: bool,
        ip: str | None,
    ) -> None:
        """
        @brief Turn simple mode on/off for a user and audit-log it.

        @param admin_user The admin performing the action.
        @param target_user_id UUID of the user to update.
        @param value New simple_mode value.
        @param ip IP address of the request.
        @raises NotFoundError If the target user is not found.
        @raises AppError FEATURE_DISABLED when turning on with the flag off.
        """
        if value:
            community = await CommunityRepository(self._session).get(self._community_id)
            if community is not None:
                require_feature(community, "simple_mode")
        target = await self._user_repo.get_by_id(target_user_id, self._community_id)
        if not target:
            raise NotFoundError(message=_("User not found"))
        repo = SettingsRepository(self._session)
        await repo.get_or_create(target_user_id, self._community_id)
        await repo.update(target_user_id, {"simple_mode": value})
        await self._audit_repo.append(
            actor_id=admin_user.id,
            action="admin.user.simple_mode",
            target_type="user",
            target_id=target_user_id,
            extra_data={"simple_mode": value},
            ip_address=ip,
        )

    async def suspend_user(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        ip: str | None,
    ) -> None:
        """
        @brief Deactivate a user (set is_active=False) and log the action.

        @param admin_user The admin performing the action.
        @param target_user_id UUID of the user to suspend.
        @param ip IP address of the request.
        @raises NotFoundError If the target user is not found.
        """
        target = await self._user_repo.get_by_id(target_user_id, self._community_id)
        if not target:
            raise NotFoundError(message=_("User not found"))
        await self._user_repo.update(target, {"is_active": False})
        await self._audit_repo.append(
            actor_id=admin_user.id,
            action="admin.user.suspended",
            target_type="user",
            target_id=target_user_id,
            extra_data=None,
            ip_address=ip,
        )
        logger.info(
            "admin_user_suspended",
            admin_id=str(admin_user.id),
            target_id=str(target_user_id),
        )

    async def restore_user(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        ip: str | None,
    ) -> None:
        """
        @brief Restore a soft-deleted user (clear deleted_at, set is_active=True).

        @param admin_user The admin performing the action.
        @param target_user_id UUID of the user to restore.
        @param ip IP address of the request.
        @raises NotFoundError If the target user is not found.
        """
        target = await self._user_repo.get_by_id_include_deleted(target_user_id, self._community_id)
        if not target:
            raise NotFoundError(message=_("User not found"))
        await self._user_repo.update(
            target,
            {"deleted_at": None, "is_active": True},
        )
        await self._audit_repo.append(
            actor_id=admin_user.id,
            action="admin.user.restored",
            target_type="user",
            target_id=target_user_id,
            extra_data=None,
            ip_address=ip,
        )
        logger.info(
            "admin_user_restored",
            admin_id=str(admin_user.id),
            target_id=str(target_user_id),
        )

    async def delete_user(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        ip: str | None,
    ) -> None:
        """
        @brief Soft-delete a user (set deleted_at and is_active=False) and log the action.

        @param admin_user The admin performing the action.
        @param target_user_id UUID of the user to delete.
        @param ip IP address of the request.
        @raises NotFoundError If the target user is not found.
        """
        target = await self._user_repo.get_by_id(target_user_id, self._community_id)
        if not target:
            raise NotFoundError(message=_("User not found"))
        await self._user_repo.update(
            target,
            {"deleted_at": datetime.now(UTC), "is_active": False},
        )
        await self._audit_repo.append(
            actor_id=admin_user.id,
            action="admin.user.deleted",
            target_type="user",
            target_id=target_user_id,
            extra_data=None,
            ip_address=ip,
        )
        logger.info(
            "admin_user_deleted",
            admin_id=str(admin_user.id),
            target_id=str(target_user_id),
        )

    async def list_users(
        self,
        *,
        search: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[User], str | None]:
        """
        @brief List community users with optional search.

        @param search Optional search string.
        @param limit Max items per page.
        @param cursor Pagination cursor.
        @return Tuple of (users, next_cursor).
        """
        return await self._user_repo.list_by_community_search(
            self._community_id,
            search=search,
            limit=limit,
            cursor=cursor,
        )

    def get_admin_settings(self) -> AdminSettingsResponse:
        """
        @brief Return admin settings from app config (Phase 1: not persisted to DB).

        @return AdminSettingsResponse.
        """
        return AdminSettingsResponse(
            enable_registration=self._settings.ENABLE_REGISTRATION,
            require_invite=self._settings.REQUIRE_INVITE,
            storage_quota_default=self._settings.STORAGE_QUOTA_DEFAULT,
            waf_enabled=self._settings.WAF_ENABLED,
        )

    async def update_admin_settings(
        self,
        admin_user: User,
        data: AdminSettingsUpdate,
        ip: str | None,
    ) -> AdminSettingsResponse:
        """
        @brief Audit log only for now (Phase 2 will persist to DB).

        @param admin_user The admin performing the action.
        @param data Partial settings update.
        @param ip IP address of the request.
        @return Current admin settings (unchanged).
        """
        changes: dict[str, Any] = data.model_dump(exclude_unset=True)
        if changes:
            await self._audit_repo.append(
                actor_id=admin_user.id,
                action="admin.settings.updated",
                target_type="settings",
                target_id=None,
                extra_data=changes,
                ip_address=ip,
            )
            logger.info("admin_settings_audited", admin_id=str(admin_user.id))
        return self.get_admin_settings()
