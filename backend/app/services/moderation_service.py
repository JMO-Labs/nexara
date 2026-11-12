"""
@file moderation_service.py
@brief Moderation business logic: reports, admin actions, user blocks,
NSFW tagging.

Every state change is appended to the audit log. Affected users are
notified (``system`` notification type) when an admin acts on their content.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_search_cache_for_community
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.i18n import _
from app.models.moderation import ContentReport, UserBlock
from app.repositories.audit_repo import AuditRepository
from app.repositories.moderation_repo import ModerationRepository

ACTIONS = {"dismiss", "warn_user", "hide_content", "delete_content", "ban_user"}
"""@brief Valid admin actions."""

_NOTIFY_TEXT = {
    "warn_user": "You received a warning from the moderators.",
    "hide_content": "Your content was hidden by the moderators.",
    "delete_content": "Your content was removed by the moderators.",
    "ban_user": "Your account was suspended by the moderators.",
}


class ModerationService:
    """
    @brief Service for content reports and user blocking.

    @param repo ModerationRepository.
    @param audit_repo AuditRepository for audit logging.
    @param community_id Community scope.
    @param notification_service Service exposing ``notify(user_id, type, payload)``.
    @param session Async DB session.
    @param invalidate Search-cache invalidation coroutine (injectable for tests).
    """

    def __init__(
        self,
        repo: ModerationRepository,
        audit_repo: AuditRepository,
        community_id: uuid.UUID,
        notification_service: Any = None,
        session: AsyncSession | None = None,
        invalidate: Callable[[uuid.UUID], Awaitable[Any]] = invalidate_search_cache_for_community,
    ) -> None:
        self._repo = repo
        self._audit = audit_repo
        self._notifier = notification_service
        self._session = session
        self._community_id = community_id
        self._invalidate = invalidate

    async def create_report(
        self,
        reporter_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        reason: str,
        description: str | None,
    ) -> ContentReport:
        """
        @brief Submit a report; one per (reporter, target).

        @param reporter_id Reporting user.
        @param target_type post, comment, media or message.
        @param target_id Reported content UUID.
        @param reason ReportReason value.
        @param description Optional details.
        @return The pending report.
        @throws NotFoundError If the target is not in this community.
        @throws ConflictError If the user already reported this target.
        """
        if not await self._repo.content_exists(target_type, target_id, self._community_id):
            raise NotFoundError(_("Reported content not found"))
        try:
            report = await self._repo.create_report(
                reporter_id=reporter_id,
                target_type=target_type,
                target_id=target_id,
                reason=reason,
                description=description,
                community_id=self._community_id,
            )
        except IntegrityError as exc:
            raise ConflictError(_("You have already reported this content")) from exc
        await self._audit.append(
            actor_id=reporter_id,
            action="moderation.report.created",
            target_type=target_type,
            target_id=target_id,
            extra_data={"report_id": str(report.id), "reason": reason},
        )
        return report

    async def list_reports(
        self, status: str | None, limit: int, cursor: str | None
    ) -> tuple[list[ContentReport], str | None]:
        """
        @brief List reports for admins, optionally filtered by status.

        @param status Status filter.
        @param limit Page size.
        @param cursor Pagination cursor.
        @return (reports, next_cursor).
        """
        return await self._repo.list_reports(
            status_filter=status,
            community_id=self._community_id,
            limit=limit,
            cursor=cursor,
        )

    async def take_action(
        self,
        report_id: uuid.UUID,
        admin_id: uuid.UUID,
        action: str,
        note: str | None,
    ) -> ContentReport:
        """
        @brief Apply an admin action to a pending report.

        @param report_id Report UUID.
        @param admin_id Acting admin.
        @param action One of ACTIONS.
        @param note Optional admin note.
        @return The updated report.
        @throws NotFoundError If the report does not exist.
        @throws ConflictError If already handled.
        """
        report = await self._repo.get_report(report_id, self._community_id)
        if report is None:
            raise NotFoundError(_("Report not found"))
        if report.status != "pending":
            raise ConflictError(_("Report has already been handled"))
        if action not in ACTIONS:
            raise AppError("VALIDATION_ERROR", _("Invalid moderation action"), 422)

        author_id = None
        if action != "dismiss":
            author_id = await self._repo.get_content_author_id(
                report.target_type, report.target_id, self._community_id
            )
        if action in ("hide_content", "delete_content"):
            await self._repo.soft_delete_content(
                report.target_type, report.target_id, self._community_id
            )
        elif action == "ban_user" and author_id is not None:
            await self._repo.deactivate_user(author_id, self._community_id)

        updated = await self._repo.mark_reviewed(
            report,
            status="dismissed" if action == "dismiss" else "reviewed",
            action_taken=action,
            admin_notes=note,
            reviewed_by=admin_id,
        )
        await self._audit.append(
            actor_id=admin_id,
            action=f"moderation.report.{action}",
            target_type=report.target_type,
            target_id=report.target_id,
            extra_data={"report_id": str(report.id), "affected_user": str(author_id)},
        )
        if author_id is not None:
            await self._notifier.notify(
                author_id,
                "system",
                {"message": _(_NOTIFY_TEXT[action]), "report_id": str(report.id)},
                admin_id,
            )
        return updated

    async def block_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlock:
        """
        @brief Block another user.

        @param blocker_id Current user.
        @param blocked_id User to block.
        @return The block record.
        @throws AppError If blocking self.
        @throws NotFoundError If the user is not in this community.
        @throws ConflictError If already blocked.
        """
        if blocker_id == blocked_id:
            raise AppError("VALIDATION_ERROR", _("You cannot block yourself"), 422)
        if not await self._repo.user_exists(blocked_id, self._community_id):
            raise NotFoundError(_("User not found"))
        if await self._repo.is_blocked(blocker_id, blocked_id):
            raise ConflictError(_("User is already blocked"))
        block = await self._repo.create_block(blocker_id, blocked_id, self._community_id)
        await self._audit.append(
            actor_id=blocker_id,
            action="moderation.user.blocked",
            target_type="user",
            target_id=blocked_id,
        )
        return block

    async def unblock_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> None:
        """
        @brief Remove a block.

        @param blocker_id Current user.
        @param blocked_id Blocked user.
        @throws NotFoundError If no such block.
        """
        if not await self._repo.is_blocked(blocker_id, blocked_id):
            raise NotFoundError(_("Block not found"))
        await self._repo.remove_block(blocker_id, blocked_id)
        await self._audit.append(
            actor_id=blocker_id,
            action="moderation.user.unblocked",
            target_type="user",
            target_id=blocked_id,
        )

    async def list_blocks(self, blocker_id: uuid.UUID) -> list[UserBlock]:
        """
        @brief List users blocked by the current user.

        @param blocker_id Current user.
        @return Block records.
        """
        return await self._repo.list_blocks(blocker_id, self._community_id)

    async def mark_nsfw(self, kind: str, entity_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        """
        @brief Set is_nsfw=true on a post or media item.

        @param kind "posts" or "media".
        @param entity_id Target UUID.
        @param admin_id Acting admin.
        @throws NotFoundError if missing, deleted, or in another community.
        """
        if not await self._repo.set_nsfw(kind, entity_id, self._community_id):
            raise NotFoundError(_("Content not found"))
        await self._audit.append(
            actor_id=admin_id,
            action=f"{kind}.marked_nsfw",
            target_type=kind,
            target_id=entity_id,
        )
        await self._invalidate(self._community_id)
