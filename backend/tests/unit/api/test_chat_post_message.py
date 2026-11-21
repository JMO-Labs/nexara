"""
@file test_chat_post_message.py
@brief POST /chat/channels/{id}/messages delegates to ChatService.send_message.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user, get_db
from app.main import app


async def test_post_message_sends_trimmed_content():
    user = MagicMock()
    user.id = uuid.uuid4()
    channel = uuid.uuid4()
    msg = {
        "id": uuid.uuid4(),
        "channel_id": channel,
        "author": None,
        "content": "hi there",
        "edited_at": None,
        "deleted": False,
        "created_at": datetime.now(UTC),
    }
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    try:
        with patch("app.api.v1.chat.ChatService") as svc_cls:
            svc_cls.return_value.send_message = AsyncMock(return_value=msg)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                ok = await c.post(
                    f"/api/v1/chat/channels/{channel}/messages", json={"content": "  hi there "}
                )
                blank = await c.post(
                    f"/api/v1/chat/channels/{channel}/messages", json={"content": "   "}
                )
        assert ok.status_code == 201, ok.text
        assert ok.json()["content"] == "hi there"
        svc_cls.return_value.send_message.assert_awaited_once_with(user, channel, "hi there")
        assert blank.status_code in (400, 422)
    finally:
        app.dependency_overrides.clear()
