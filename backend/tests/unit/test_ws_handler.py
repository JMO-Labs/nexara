"""
@file test_ws_handler.py
@brief Unit tests for the WebSocket endpoint handler.

Tests cover first-message authentication, timeout behavior, message
loop handling, and connection lifecycle.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.ws import _authenticate, _close_safe, _message_loop
from app.core.config import Settings
from app.services.realtime.protocol import OutboundType


def _make_settings() -> Settings:
    """@brief Settings fixture for WS tests."""
    return Settings(SECRET_KEY="test-ws-secret", JWT_ALGORITHM="HS256")


class TestAuthenticate:
    """@brief First-message authentication tests."""

    @pytest.mark.asyncio
    async def test_valid_auth_returns_user_id(self):
        from app.core.security import create_access_token

        settings = _make_settings()
        user_id = uuid.uuid4()
        token = create_access_token(user_id, settings=settings)

        auth_msg = json.dumps(
            {
                "type": "auth",
                "payload": {"token": token},
            }
        )

        ws = AsyncMock()
        ws.receive_text = AsyncMock(return_value=auth_msg)
        ws.send_text = AsyncMock()
        ws.client_state = MagicMock()

        with patch("app.api.v1.ws.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": str(user_id), "type": "access"}
            result = await _authenticate(ws)

        assert result == user_id
        ws.send_text.assert_called_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == OutboundType.AUTH_OK

    @pytest.mark.asyncio
    async def test_missing_token_closes_4001(self):
        auth_msg = json.dumps({"type": "auth", "payload": {}})

        ws = AsyncMock()
        ws.receive_text = AsyncMock(return_value=auth_msg)
        ws.send_text = AsyncMock()
        ws.client_state = MagicMock()

        with patch("app.api.v1.ws._close_safe", new_callable=AsyncMock):
            result = await _authenticate(ws)

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_first_message_type_closes(self):
        msg = json.dumps({"type": "ping"})

        ws = AsyncMock()
        ws.receive_text = AsyncMock(return_value=msg)
        ws.client_state = MagicMock()

        with patch("app.api.v1.ws._close_safe", new_callable=AsyncMock) as mock_close:
            result = await _authenticate(ws)

        assert result is None
        mock_close.assert_called_once()
        assert mock_close.call_args[0][1] == 4001

    @pytest.mark.asyncio
    async def test_invalid_json_closes_4002(self):
        ws = AsyncMock()
        ws.receive_text = AsyncMock(return_value="not json")
        ws.client_state = MagicMock()

        with patch("app.api.v1.ws._close_safe", new_callable=AsyncMock) as mock_close:
            result = await _authenticate(ws)

        assert result is None
        mock_close.assert_called_once()
        assert mock_close.call_args[0][1] == 4002

    @pytest.mark.asyncio
    async def test_timeout_closes_4001(self):
        import asyncio

        ws = AsyncMock()
        ws.receive_text = AsyncMock(side_effect=asyncio.TimeoutError)
        ws.client_state = MagicMock()

        with patch("app.api.v1.ws._close_safe", new_callable=AsyncMock) as mock_close:
            result = await _authenticate(ws)

        assert result is None
        mock_close.assert_called_once()
        assert mock_close.call_args[0][1] == 4001


class TestMessageLoop:
    """@brief Message loop dispatch tests."""

    @pytest.mark.asyncio
    async def test_ping_sends_pong(self):
        from fastapi import WebSocketDisconnect

        ws = AsyncMock()
        user_id = uuid.uuid4()

        call_count = 0

        async def mock_receive():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps({"type": "ping"})
            raise WebSocketDisconnect()

        ws.receive_text = mock_receive
        ws.send_text = AsyncMock()

        with (
            patch("app.api.v1.ws.set_online", new_callable=AsyncMock),
            pytest.raises(WebSocketDisconnect),
        ):
            await _message_loop(ws, user_id)

        ws.send_text.assert_called_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == OutboundType.PONG


class TestCloseSafe:
    """@brief Safe WebSocket close tests."""

    @pytest.mark.asyncio
    async def test_closes_connected_socket(self):
        from starlette.websockets import WebSocketState

        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.close = AsyncMock()

        await _close_safe(ws, 4001, "test")
        ws.close.assert_called_once_with(code=4001, reason="test")

    @pytest.mark.asyncio
    async def test_ignores_already_closed(self):
        from starlette.websockets import WebSocketState

        ws = AsyncMock()
        ws.client_state = WebSocketState.DISCONNECTED
        ws.close = AsyncMock()

        await _close_safe(ws, 4001, "test")
        ws.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_swallows_close_errors(self):
        from starlette.websockets import WebSocketState

        ws = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.close = AsyncMock(side_effect=RuntimeError("already closed"))

        await _close_safe(ws, 4001, "test")
