"""
@file test_moderation_service.py
@brief Admin NSFW marking: sets flag, audit-logs, invalidates search cache.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.services.moderation_service import ModerationService

CID = uuid.uuid4()


def _svc(found: bool = True):
    repo = AsyncMock()
    repo.set_nsfw.return_value = found
    audit = AsyncMock()
    return ModerationService(repo, audit, CID), repo, audit


@pytest.mark.parametrize("kind", ["post", "media"])
async def test_mark_nsfw_sets_audits_and_invalidates(kind):
    svc, repo, audit = _svc()
    admin = MagicMock(id=uuid.uuid4())
    tid = uuid.uuid4()
    with patch(
        "app.services.moderation_service.invalidate_search_cache_for_community",
        new=AsyncMock(),
    ) as inv:
        await svc.mark_nsfw(kind, tid, admin, "1.2.3.4")
    repo.set_nsfw.assert_awaited_once_with(kind, tid, CID, True)
    assert audit.append.await_args.kwargs["action"] == f"moderation.{kind}.marked_nsfw"
    inv.assert_awaited_once()


async def test_mark_nsfw_not_found():
    svc, _, audit = _svc(found=False)
    with pytest.raises(NotFoundError):
        await svc.mark_nsfw("post", uuid.uuid4(), MagicMock(id=uuid.uuid4()), None)
    audit.append.assert_not_awaited()
