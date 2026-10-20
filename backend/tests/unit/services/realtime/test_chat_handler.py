"""
@file test_chat_handler.py
@brief Unit tests for the chat WebSocket handler.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.realtime.handlers.chat_handler import (
    _handle_read,
    _handle_typing,
    _send_error,
    handle_chat_inbound,
)


@pytest.fixture
def ws() -> AsyncMock:
    """@brief Mock WebSocket with send_text coroutine."""
    mock = AsyncMock()
    mock.send_text = AsyncMock()
    return mock


class TestSendError:
    """@brief Tests for _send_error()."""

    @pytest.mark.asyncio
    async def test_send_error_envelope(self, ws) -> None:
        """_send_error writes a chat.error JSON frame with code and message."""
        await _send_error(ws, "VALIDATION_ERROR", "bad")
        ws.send_text.assert_awaited_once()
        raw = ws.send_text.call_args[0][0]
        data = json.loads(raw)
        assert data["type"] == "chat.error"
        assert data["payload"]["code"] == "VALIDATION_ERROR"
        assert data["payload"]["message"] == "bad"

    @pytest.mark.asyncio
    async def test_send_error_ignores_failures(self, ws) -> None:
        """_send_error swallows exceptions raised by send_text."""
        ws.send_text.side_effect = RuntimeError("dropped")
        await _send_error(ws, "X", "y")


class TestHandleChatInboundDispatch:
    """@brief Tests for handle_chat_inbound() routing."""

    @pytest.mark.asyncio
    async def test_unknown_type_is_ignored(self, ws) -> None:
        """Unknown chat.* subtype is logged but never sends an error frame."""
        await handle_chat_inbound(ws, uuid.uuid4(), "chat.mystery", {})
        ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.handlers.chat_handler._handle_typing",
        new_callable=AsyncMock,
    )
    async def test_typing_routed(self, mock_typing, ws) -> None:
        """chat.typing frames are dispatched to _handle_typing."""
        uid = uuid.uuid4()
        await handle_chat_inbound(
            ws, uid, "chat.typing", {"payload": {"channel_id": str(uuid.uuid4())}}
        )
        mock_typing.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.handlers.chat_handler._handle_read",
        new_callable=AsyncMock,
    )
    async def test_read_routed(self, mock_read, ws) -> None:
        """chat.read frames are dispatched to _handle_read."""
        uid = uuid.uuid4()
        payload = {"channel_id": str(uuid.uuid4()), "message_id": str(uuid.uuid4())}
        await handle_chat_inbound(ws, uid, "chat.read", {"payload": payload})
        mock_read.assert_awaited_once()


class TestHandleTyping:
    """@brief Tests for _handle_typing()."""

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish",
        new_callable=AsyncMock,
    )
    async def test_publishes_chat_typing_envelope(self, mock_publish) -> None:
        """_handle_typing publishes a chat.typing envelope on chat:{id}."""
        uid = uuid.uuid4()
        cid = uuid.uuid4()
        await _handle_typing(uid, {"channel_id": str(cid)})
        mock_publish.assert_awaited_once()
        channel, envelope = mock_publish.call_args[0]
        assert channel == f"chat:{cid}"
        assert envelope["type"] == "chat.typing"
        assert envelope["payload"]["user_id"] == str(uid)
        assert envelope["payload"]["channel_id"] == str(cid)

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish",
        new_callable=AsyncMock,
    )
    async def test_missing_channel_id_is_noop(self, mock_publish) -> None:
        """_handle_typing with no channel_id does nothing."""
        await _handle_typing(uuid.uuid4(), {})
        mock_publish.assert_not_awaited()

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish",
        new_callable=AsyncMock,
    )
    async def test_bad_channel_id_is_noop(self, mock_publish) -> None:
        """_handle_typing with malformed channel_id does nothing."""
        await _handle_typing(uuid.uuid4(), {"channel_id": "not-a-uuid"})
        mock_publish.assert_not_awaited()


class TestHandleRead:
    """@brief Tests for _handle_read()."""

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish",
        new_callable=AsyncMock,
    )
    async def test_publishes_chat_read_envelope(self, mock_publish) -> None:
        """_handle_read publishes a chat.read envelope with user, channel, message."""
        uid = uuid.uuid4()
        cid = uuid.uuid4()
        mid = uuid.uuid4()
        await _handle_read(uid, {"channel_id": str(cid), "message_id": str(mid)})
        channel, envelope = mock_publish.call_args[0]
        assert channel == f"chat:{cid}"
        assert envelope["type"] == "chat.read"
        assert envelope["payload"]["message_id"] == str(mid)

    @pytest.mark.asyncio
    @patch(
        "app.services.realtime.pubsub.publish",
        new_callable=AsyncMock,
    )
    async def test_missing_fields_are_noop(self, mock_publish) -> None:
        """_handle_read with missing fields does not publish."""
        await _handle_read(uuid.uuid4(), {"channel_id": str(uuid.uuid4())})
        mock_publish.assert_not_awaited()


class TestHandleMessageValidation:
    """@brief Tests for the ``chat.message`` branch input validation."""

    @pytest.mark.asyncio
    async def test_missing_channel_id_sends_error(self, ws) -> None:
        """chat.message without channel_id emits a VALIDATION_ERROR frame."""
        await handle_chat_inbound(ws, uuid.uuid4(), "chat.message", {"payload": {"content": "hi"}})
        ws.send_text.assert_awaited_once()
        data = json.loads(ws.send_text.call_args[0][0])
        assert data["type"] == "chat.error"
        assert data["payload"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_blank_content_sends_error(self, ws) -> None:
        """chat.message with empty content emits a VALIDATION_ERROR frame."""
        await handle_chat_inbound(
            ws,
            uuid.uuid4(),
            "chat.message",
            {"payload": {"channel_id": str(uuid.uuid4()), "content": "   "}},
        )
        ws.send_text.assert_awaited_once()
        data = json.loads(ws.send_text.call_args[0][0])
        assert data["payload"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_bad_channel_id_sends_error(self, ws) -> None:
        """chat.message with malformed channel_id emits a VALIDATION_ERROR frame."""
        await handle_chat_inbound(
            ws,
            uuid.uuid4(),
            "chat.message",
            {"payload": {"channel_id": "nope", "content": "hi"}},
        )
        ws.send_text.assert_awaited_once()
        data = json.loads(ws.send_text.call_args[0][0])
        assert data["payload"]["code"] == "VALIDATION_ERROR"
