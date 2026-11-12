"""
@file metrics.py
@brief Prometheus custom application metrics.

Beyond the auto-instrumented HTTP metrics provided by
``prometheus-fastapi-instrumentator``, these gauges and counters
expose application-level observability for Grafana dashboards.

Metrics are incremented inline in service calls (negligible cost).
Gauge values that require database queries are refreshed by a periodic
Celery task (``refresh_prometheus_gauges``, every 60 s).
"""

from prometheus_client import Counter, Gauge

# ── Active connections ────────────────────────────────────────────────────

ws_connections_active: Gauge = Gauge(
    "nexara_websocket_connections_active",
    "Number of currently active WebSocket connections",
)
"""@brief Gauge tracking live WebSocket connections."""

sse_connections_active: Gauge = Gauge(
    "nexara_sse_connections_active",
    "Number of currently active SSE streams",
)
"""@brief Gauge tracking live SSE notification streams."""

# ── Community activity ────────────────────────────────────────────────────

posts_created_total: Counter = Counter(
    "nexara_posts_created_total",
    "Total number of posts created",
)
"""@brief Counter incremented on each new post."""

chat_messages_total: Counter = Counter(
    "nexara_chat_messages_total",
    "Total number of chat messages sent",
)
"""@brief Counter incremented on each new chat message."""

media_uploaded_bytes_total: Counter = Counter(
    "nexara_media_uploaded_bytes_total",
    "Total bytes of media uploaded",
)
"""@brief Counter tracking cumulative upload volume."""

events_created_total: Counter = Counter(
    "nexara_events_created_total",
    "Total number of calendar events created",
)
"""@brief Counter incremented on each new event."""

# ── Storage ───────────────────────────────────────────────────────────────

storage_used_bytes: Gauge = Gauge(
    "nexara_storage_used_bytes",
    "Total bytes of media storage currently in use",
)
"""@brief Gauge refreshed by periodic Celery task."""

# ── Users ─────────────────────────────────────────────────────────────────

users_total: Gauge = Gauge(
    "nexara_users_total",
    "Total number of registered users",
    ["role"],
)
"""@brief Gauge with ``role`` label (admin, member, viewer)."""

users_online: Gauge = Gauge(
    "nexara_users_online",
    "Number of users currently online (presence)",
)
"""@brief Gauge updated by the presence subsystem."""

# ── WAF ───────────────────────────────────────────────────────────────────

waf_blocks_total: Counter = Counter(
    "nexara_waf_blocks_total",
    "Total number of requests blocked by WAF",
    ["reason"],
)
"""@brief Counter with ``reason`` label (SQL_INJECTION, PATH_TRAVERSAL, etc.)."""

# ── Celery ────────────────────────────────────────────────────────────────

celery_queue_depth: Gauge = Gauge(
    "nexara_celery_queue_depth",
    "Number of tasks waiting in Celery queue",
    ["queue"],
)
"""@brief Gauge with ``queue`` label refreshed by periodic task."""

# ── Search cache ──────────────────────────────────────────────────────────

search_cache_hits_total: Counter = Counter(
    "search_cache_hits_total",
    "Search results served from the Valkey cache",
    ["community_id"],
)
"""@brief Counter of search cache hits."""

search_cache_misses_total: Counter = Counter(
    "search_cache_misses_total",
    "Search first-page lookups not found in the Valkey cache",
    ["community_id"],
)
"""@brief Counter of search cache misses."""

search_cache_invalidations_total: Counter = Counter(
    "search_cache_invalidations_total",
    "Number of times the search cache was invalidated",
    ["community_id"],
)
"""@brief Counter of search cache invalidations."""

ocr_processed_total: Counter = Counter(
    "nexara_ocr_processed_total",
    "OCR task outcomes",
    ["status"],
)

ai_usage_cents_total: Counter = Counter(
    "ai_usage_cents_total",
    "Cumulative AI spend in cents",
    ["model", "provider", "feature"],
)
ai_calls_total: Counter = Counter(
    "ai_calls_total",
    "AI call count",
    ["model", "provider", "feature"],
)
ai_budget_exceeded_total: Counter = Counter(
    "ai_budget_exceeded_total",
    "Times the daily AI budget blocked a call",
    ["community_id"],
)
