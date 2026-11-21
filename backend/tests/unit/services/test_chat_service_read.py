"""
@file test_chat_service_read.py
@brief ChatService read-marker behaviour (mark_read, send_message auto-read).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.chat_read_repo import ChatReadRepository
from app.repositories.chat_repo import ChatChannelRepository, ChatMessageRepository
from app.services.chat_service import ChatService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _build(channel_found: bool = True):
    channel_repo = AsyncMock(spec=ChatChannelRepository)
    channel = MagicMock()
    channel.id = uuid.uuid4()
    channel.channel_type = "community"
    channel_repo.get_for_user.return_value = channel if channel_found else None
    message_repo = AsyncMock(spec=ChatMessageRepository)
    message_repo.create_message.return_value = MagicMock(
        id=uuid.uuid4(), content="hi", created_at=MagicMock(isoformat=lambda: "t"), edited_at=None
    )
    read_repo = AsyncMock(spec=ChatReadRepository)
    svc = ChatService(
        channel_repo,
        message_repo,
        COMMUNITY_ID,
        broadcaster=AsyncMock(),
        link_preview_enqueue=MagicMock(),
        read_repo=read_repo,
    )
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return svc, read_repo, channel, user


async def test_mark_read_upserts_for_accessible_channel():
    svc, read_repo, channel, user = _build()
    await svc.mark_read(user, channel.id)
    read_repo.mark_read.assert_awaited_once_with(user.id, channel.id, COMMUNITY_ID)


async def test_mark_read_unknown_channel_raises_not_found():
    svc, read_repo, channel, user = _build(channel_found=False)
    with pytest.raises(NotFoundError):
        await svc.mark_read(user, channel.id)
    read_repo.mark_read.assert_not_awaited()


async def test_send_message_marks_channel_read():
    svc, read_repo, channel, user = _build()
    await svc.send_message(user, channel.id, "hi")
    read_repo.mark_read.assert_awaited_once_with(user.id, channel.id, COMMUNITY_ID)
