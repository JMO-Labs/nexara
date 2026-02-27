"""
@file test_metrics.py
@brief Unit tests for Prometheus custom application metrics.
"""

from prometheus_client import CollectorRegistry

from app.core.metrics import (
    celery_queue_depth,
    chat_messages_total,
    events_created_total,
    media_uploaded_bytes_total,
    posts_created_total,
    sse_connections_active,
    storage_used_bytes,
    users_online,
    users_total,
    waf_blocks_total,
    ws_connections_active,
)


class TestMetricsExist:
    """@brief Verify all application metrics are registered."""

    def test_ws_connections_active(self):
        assert "nexara_websocket_connections_active" in ws_connections_active._name

    def test_sse_connections_active(self):
        assert "nexara_sse_connections_active" in sse_connections_active._name

    def test_posts_created_total(self):
        assert "nexara_posts_created" in posts_created_total._name

    def test_chat_messages_total(self):
        assert "nexara_chat_messages" in chat_messages_total._name

    def test_media_uploaded_bytes_total(self):
        assert "nexara_media_uploaded_bytes" in media_uploaded_bytes_total._name

    def test_events_created_total(self):
        assert "nexara_events_created" in events_created_total._name

    def test_storage_used_bytes(self):
        assert "nexara_storage_used_bytes" in storage_used_bytes._name

    def test_users_total(self):
        assert "nexara_users_total" in users_total._name

    def test_users_online(self):
        assert "nexara_users_online" in users_online._name

    def test_waf_blocks_total(self):
        assert "nexara_waf_blocks" in waf_blocks_total._name

    def test_celery_queue_depth(self):
        assert "nexara_celery_queue_depth" in celery_queue_depth._name
