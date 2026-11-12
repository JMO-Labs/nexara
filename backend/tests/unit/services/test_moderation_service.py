"""
@file test_moderation_service.py
@brief Unit tests for ModerationService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.moderation import ContentReport
from app.repositories.audit_repo import AuditRepository
from app.repositories.moderation_repo import ModerationRepository
from app.services.moderation_service import ModerationService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
AUTHOR_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()


@pytest.fixture
def repo():
    return AsyncMock(spec=ModerationRepository)


@pytest.fixture
def audit():
    return AsyncMock(spec=AuditRepository)


@pytest.fixture
def notifier():
    return AsyncMock()


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def service(repo, audit, notifier, session):
    return ModerationService(
        repo=repo,
        audit_repo=audit,
        notification_service=notifier,
        session=session,
        community_id=COMMUNITY_ID,
    )


def _report(status="pending"):
    r = MagicMock(spec=ContentReport)
    r.id = uuid.uuid4()
    r.reporter_id = USER_ID
    r.target_type = "post"
    r.target_id = TARGET_ID
    r.status = status
    return r


class TestCreateReport:
    async def test_creates_pending_and_audits(self, service, repo, audit):
        repo.create_report.return_value = _report()
        result = await service.create_report(USER_ID, "post", TARGET_ID, "spam", None)
        assert result.status == "pending"
        repo.create_report.assert_awaited_once()
        audit.append.assert_awaited_once()
        assert audit.append.call_args.kwargs["action"] == "moderation.report.created"

    async def test_duplicate_rejected(self, service, repo):
        repo.create_report.side_effect = IntegrityError("x", {}, Exception())
        with pytest.raises(ConflictError):
            await service.create_report(USER_ID, "post", TARGET_ID, "spam", None)


class TestAction:
    async def test_not_found(self, service, repo):
        repo.get_report.return_value = None
        with pytest.raises(NotFoundError):
            await service.take_action(uuid.uuid4(), ADMIN_ID, "dismiss", None)

    async def test_dismiss_sets_dismissed_no_notify(self, service, repo, audit, notifier):
        report = _report()
        repo.get_report.return_value = report
        repo.mark_reviewed.return_value = report
        await service.take_action(report.id, ADMIN_ID, "dismiss", "ok")
        assert repo.mark_reviewed.call_args.kwargs["status"] == "dismissed"
        audit.append.assert_awaited_once()
        notifier.notify.assert_not_awaited()

    async def test_warn_notifies_author_and_audits(self, service, repo, audit, notifier):
        report = _report()
        repo.get_report.return_value = report
        repo.mark_reviewed.return_value = report
        repo.get_content_author_id.return_value = AUTHOR_ID
        await service.take_action(report.id, ADMIN_ID, "warn_user", None)
        assert repo.mark_reviewed.call_args.kwargs["status"] == "reviewed"
        assert notifier.notify.call_args.args[0] == AUTHOR_ID
        assert audit.append.call_args.kwargs["action"] == "moderation.report.warn_user"

    async def test_ban_deactivates_author(self, service, repo):
        report = _report()
        repo.get_report.return_value = report
        repo.mark_reviewed.return_value = report
        repo.get_content_author_id.return_value = AUTHOR_ID
        await service.take_action(report.id, ADMIN_ID, "ban_user", None)
        repo.deactivate_user.assert_awaited_once_with(AUTHOR_ID)

    async def test_delete_content_removes_content(self, service, repo):
        report = _report()
        repo.get_report.return_value = report
        repo.mark_reviewed.return_value = report
        repo.get_content_author_id.return_value = AUTHOR_ID
        await service.take_action(report.id, ADMIN_ID, "delete_content", None)
        repo.soft_delete_content.assert_awaited_once_with("post", TARGET_ID)

    async def test_already_reviewed_conflict(self, service, repo):
        repo.get_report.return_value = _report(status="reviewed")
        with pytest.raises(ConflictError):
            await service.take_action(uuid.uuid4(), ADMIN_ID, "dismiss", None)

    async def test_invalid_action(self, service, repo):
        repo.get_report.return_value = _report()
        with pytest.raises(AppError):
            await service.take_action(uuid.uuid4(), ADMIN_ID, "nuke", None)


class TestBlocks:
    async def test_block_creates_and_audits(self, service, repo, audit):
        repo.is_blocked.return_value = False
        await service.block_user(USER_ID, AUTHOR_ID)
        repo.create_block.assert_awaited_once_with(USER_ID, AUTHOR_ID, COMMUNITY_ID)
        assert audit.append.call_args.kwargs["action"] == "moderation.user.blocked"

    async def test_block_self_rejected(self, service):
        with pytest.raises(AppError):
            await service.block_user(USER_ID, USER_ID)

    async def test_block_existing_is_conflict(self, service, repo):
        repo.is_blocked.return_value = True
        with pytest.raises(ConflictError):
            await service.block_user(USER_ID, AUTHOR_ID)

    async def test_unblock_audits(self, service, repo, audit):
        repo.is_blocked.return_value = True
        await service.unblock_user(USER_ID, AUTHOR_ID)
        repo.remove_block.assert_awaited_once_with(USER_ID, AUTHOR_ID)
        assert audit.append.call_args.kwargs["action"] == "moderation.user.unblocked"

    async def test_unblock_missing_not_found(self, service, repo):
        repo.is_blocked.return_value = False
        with pytest.raises(NotFoundError):
            await service.unblock_user(USER_ID, AUTHOR_ID)
