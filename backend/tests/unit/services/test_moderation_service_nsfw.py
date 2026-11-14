"""
@file test_moderation_service_nsfw.py
@brief Unit tests for ModerationService (NSFW tagging, audit, cache bust).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.repositories.moderation_repo import ModerationRepository
from app.services.moderation_service import ModerationService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize("kind", ["posts", "media"])
async def test_mark_nsfw_audits_and_invalidates(kind) -> None:
    repo = AsyncMock(spec=ModerationRepository)
    repo.set_nsfw.return_value = True
    audit, invalidate = AsyncMock(), AsyncMock()
    target, admin = uuid.uuid4(), uuid.uuid4()

    await ModerationService(repo, audit, CID, invalidate=invalidate).mark_nsfw(kind, target, admin)

    repo.set_nsfw.assert_awaited_once_with(kind, target, CID)
    audit.append.assert_awaited_once_with(
        actor_id=admin, action=f"{kind}.marked_nsfw", target_type=kind, target_id=target
    )
    invalidate.assert_awaited_once_with(CID)


async def test_mark_nsfw_missing_raises_without_side_effects() -> None:
    repo = AsyncMock(spec=ModerationRepository)
    repo.set_nsfw.return_value = False
    audit, invalidate = AsyncMock(), AsyncMock()
    svc = ModerationService(repo, audit, CID, invalidate=invalidate)

    with pytest.raises(NotFoundError):
        await svc.mark_nsfw("posts", uuid.uuid4(), uuid.uuid4())

    audit.append.assert_not_awaited()
    invalidate.assert_not_awaited()
