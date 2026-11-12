"""
@file celery_app.py
@brief Celery application, configuration, task routing, and Beat schedule.

Serves as the entry point for ``celery -A app.tasks.celery_app worker`` and
``celery -A app.tasks.celery_app beat``.  All configuration is drawn from
:class:`app.core.config.Settings` environment variables.
"""

from __future__ import annotations

from typing import Any

import structlog
from celery import Celery, signals
from celery.schedules import crontab

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

celery_app = Celery("nexara")
"""@brief The Celery application instance."""

celery_app.conf.update(
    # ── Broker & result backend ───────────────────────────────────────
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_broker_url,
    # ── Serialization ─────────────────────────────────────────────────
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # ── Task routing ──────────────────────────────────────────────────
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.media_tasks.*": {"queue": "media"},
        "app.tasks.ai_tasks.*": {"queue": "media"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "app.tasks.poll_tasks.*": {"queue": "maintenance"},
        "app.tasks.birthday_tasks.*": {"queue": "notifications"},
        "app.tasks.event_tasks.dispatch_event_reminders": {"queue": "notifications"},
        "app.tasks.event_tasks.sync_subscriptions": {"queue": "maintenance"},
        "app.tasks.prompt_tasks.*": {"queue": "maintenance"},
        "app.tasks.retention_tasks.*": {"queue": "maintenance"},
        "app.tasks.nudge_tasks.*": {"queue": "maintenance"},
        "app.tasks.export_tasks.*": {"queue": "maintenance"},
    },
    # ── Reliability ───────────────────────────────────────────────────
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    # ── Result TTL ────────────────────────────────────────────────────
    result_expires=3600,
    # ── Time limits (overridable per task) ────────────────────────────
    task_soft_time_limit=60,
    task_time_limit=120,
    # ── Beat schedule ─────────────────────────────────────────────────
    beat_schedule={
        "refresh-prometheus-gauges": {
            "task": "app.tasks.maintenance_tasks.refresh_prometheus_gauges",
            "schedule": 60.0,
        },
        "ai-budget-reset": {
            "task": "app.tasks.maintenance_tasks.reset_ai_daily_budget",
            "schedule": crontab(hour=settings.AI_BUDGET_RESET_HOUR, minute=0),
        },
        "close-expired-polls": {
            "task": "app.tasks.poll_tasks.close_expired_polls",
            "schedule": 60.0,
        },
        "cleanup-expired-tokens": {
            "task": "app.tasks.maintenance_tasks.cleanup_expired_tokens",
            "schedule": crontab(minute=0, hour="*/1"),
        },
        "recalculate-quotas": {
            "task": "app.tasks.maintenance_tasks.recalculate_storage_quotas",
            "schedule": crontab(hour="3", minute="0"),
        },
        "database-backup": {
            "task": "app.tasks.maintenance_tasks.database_backup",
            "schedule": crontab(hour="0", minute="30"),
        },
        "cleanup-orphaned-media": {
            "task": "app.tasks.media_tasks.delete_orphaned_media",
            "schedule": crontab(hour="*/6"),
        },
        "dispatch-event-reminders": {
            "task": "app.tasks.event_tasks.dispatch_event_reminders",
            "schedule": crontab(minute="*/15"),
        },
        "sync-calendar-subscriptions": {
            "task": "app.tasks.event_tasks.sync_subscriptions",
            "schedule": crontab(minute="0"),
        },
        "fire-tradition-prompts": {
            "task": "app.tasks.prompt_tasks.fire_prompts",
            "schedule": crontab(hour="6", minute="0"),
        },
        "generate-prompt-summaries": {
            "task": "app.tasks.prompt_tasks.generate_summaries",
            "schedule": crontab(hour="7", minute="0"),
        },
        "storage-snapshot": {
            "task": "app.tasks.retention_tasks.take_storage_snapshot",
            "schedule": crontab(hour="1", minute="0"),
        },
        "age-chat-messages": {
            "task": "app.tasks.retention_tasks.age_chat_messages",
            "schedule": crontab(hour="2", minute="0"),
        },
        "age-notifications": {
            "task": "app.tasks.retention_tasks.age_notifications",
            "schedule": crontab(hour="2", minute="15"),
        },
        "purge-soft-deleted-posts": {
            "task": "app.tasks.retention_tasks.purge_soft_deleted_posts",
            "schedule": crontab(hour="2", minute="30"),
        },
        "purge-soft-deleted-users": {
            "task": "app.tasks.retention_tasks.purge_soft_deleted_users",
            "schedule": crontab(hour="2", minute="45"),
        },
        "cleanup-link-previews": {
            "task": "app.tasks.retention_tasks.cleanup_expired_link_previews",
            "schedule": crontab(hour="3", minute="0"),
        },
        "age-audit-logs": {
            "task": "app.tasks.retention_tasks.age_audit_logs",
            "schedule": crontab(day_of_week="sun", hour="3", minute="15"),
        },
        "age-ai-usage-logs": {
            "task": "app.tasks.retention_tasks.age_ai_usage_logs",
            "schedule": crontab(hour="3", minute="30"),
        },
        "age-post-media": {
            "task": "app.tasks.retention_tasks.age_post_media",
            "schedule": crontab(day_of_week="sat", hour="4", minute="0"),
        },
        "age-posts": {
            "task": "app.tasks.retention_tasks.age_posts",
            "schedule": crontab(day_of_week="sat", hour="4", minute="30"),
        },
        "gallery-post-event-reminders": {
            "task": "app.tasks.gallery_tasks.gallery_post_event_reminders",
            "schedule": crontab(hour="9", minute="0"),
        },
        "gallery-batch-notifications": {
            "task": "app.tasks.gallery_tasks.gallery_batch_notifications",
            "schedule": 60.0 * 60,
        },
        "send-birthday-reminders": {
            "task": "app.tasks.birthday_tasks.send_birthday_reminders",
            "schedule": crontab(hour="6", minute="0"),
        },
        "send-gentle-nudges": {
            "task": "app.tasks.nudge_tasks.send_gentle_nudges",
            "schedule": crontab(hour="10", minute="0"),
        },
        "prune-activity-events": {
            "task": "app.tasks.maintenance_tasks.prune_activity_events",
            "schedule": crontab(hour="1", minute="0"),
        },
    },
)


@signals.worker_init.connect  # type: ignore[untyped-decorator]
def _on_worker_init(**kwargs: object) -> None:
    """
    @brief Hook executed when a Celery worker starts.

    Logs startup info for observability.
    """
    logger.info(
        "celery_worker_started",
        broker=settings.celery_broker_url,
        queues=list(celery_app.conf.task_routes.keys()),
    )


@signals.task_prerun.connect  # type: ignore[untyped-decorator]
def _on_task_prerun(task_id: str, task: Any, **kwargs: object) -> None:
    """@brief Log each task start for structured logging correlation."""
    logger.info("celery_task_started", task_id=task_id, task_name=task.name)


@signals.task_postrun.connect  # type: ignore[untyped-decorator]
def _on_task_postrun(
    task_id: str, task: Any, retval: object, state: object, **kwargs: object
) -> None:
    """@brief Log each task completion with its result state."""
    logger.info("celery_task_finished", task_id=task_id, task_name=task.name, state=state)


@signals.task_failure.connect  # type: ignore[untyped-decorator]
def _on_task_failure(task_id: str, exception: BaseException, **kwargs: object) -> None:
    """@brief Log task failures for alerting and debugging."""
    logger.error(
        "celery_task_failed",
        task_id=task_id,
        exception=str(exception),
        exc_info=True,
    )


@signals.import_modules.connect(sender=celery_app)  # type: ignore[untyped-decorator]
def _load_plugin_tasks(**kwargs: object) -> None:
    """@brief Register plugin Celery tasks and Beat entries when worker/beat start."""
    from app.plugins.task_loader import load_plugin_tasks

    logger.info("plugin_tasks_loaded", plugins=load_plugin_tasks())
