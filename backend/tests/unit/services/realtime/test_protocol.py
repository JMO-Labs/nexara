"""
@file test_protocol.py
@brief Unit tests for realtime message protocol serialization and deserialization.
"""

from __future__ import annotations

import json

from app.services.realtime.protocol import (
    BaseMessage,
    InboundType,
    OutboundType,
    build_outbound,
    build_sse_event,
    parse_inbound,
)


class TestBaseMessage:
    """@brief Verify base message structure."""

    def test_default_fields(self):
        msg = BaseMessage(type="test")
        assert msg.type == "test"
        assert msg.payload == {}
        assert msg.ts

    def test_custom_payload(self):
        msg = BaseMessage(type="test", payload={"key": "value"})
        assert msg.payload["key"] == "value"


class TestInboundTypes:
    """@brief Verify inbound message type enum values."""

    def test_auth(self):
        assert InboundType.AUTH == "auth"

    def test_ping(self):
        assert InboundType.PING == "ping"

    def test_typing(self):
        assert InboundType.TYPING == "typing"


class TestOutboundTypes:
    """@brief Verify outbound message type enum values."""

    def test_all_types_present(self):
        expected = {
            "auth_ok", "auth_error", "pong", "notification",
            "feed_update", "presence", "typing",
        }
        actual = {t.value for t in OutboundType}
        assert expected == actual


class TestParseInbound:
    """@brief Verify inbound message parsing."""

    def test_parse_auth(self):
        raw = {"type": "auth", "payload": {"token": "jwt-here"}}
        msg = parse_inbound(raw)
        assert msg.type == "auth"
        assert msg.payload["token"] == "jwt-here"

    def test_parse_ping(self):
        msg = parse_inbound({"type": "ping"})
        assert msg.type == "ping"

    def test_parse_unknown_type(self):
        msg = parse_inbound({"type": "unknown", "payload": {}})
        assert msg.type == "unknown"


class TestBuildOutbound:
    """@brief Verify outbound message serialization."""

    def test_builds_json_string(self):
        result = build_outbound(OutboundType.PONG)
        data = json.loads(result)
        assert data["type"] == "pong"
        assert "ts" in data

    def test_includes_payload(self):
        result = build_outbound(OutboundType.AUTH_OK, {"user_id": "abc"})
        data = json.loads(result)
        assert data["payload"]["user_id"] == "abc"


class TestBuildSSEEvent:
    """@brief Verify SSE event formatting."""

    def test_basic_event(self):
        result = build_sse_event("notification", {"title": "Hello"})
        assert "event: notification\n" in result
        assert '"title": "Hello"' in result
        assert result.endswith("\n\n")

    def test_with_event_id(self):
        result = build_sse_event("feed_update", {"id": 1}, event_id="42")
        assert "id: 42\n" in result

    def test_without_event_id(self):
        result = build_sse_event("test", {})
        assert "id:" not in result
