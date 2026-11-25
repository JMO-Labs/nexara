"""
@file test_worker_queues.py
@brief Contract: every queue a task can be routed to is consumed by the supervisord worker.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from app.tasks.celery_app import celery_app

CONF = Path(__file__).parents[4] / "deploy/supervisord/conf.d/celery-worker.conf"


def _worker_queues() -> set[str]:
    m = re.search(r"^command=.*\s-Q\s+(\S+)", CONF.read_text(), re.M)
    assert m, "celery-worker.conf has no -Q option"
    return set(m.group(1).split(","))


def _routed_queues() -> set[str]:
    for mod in celery_app.conf.include:
        importlib.import_module(mod)
    queues = {celery_app.conf.task_default_queue}
    queues |= {r["queue"] for r in celery_app.conf.task_routes.values()}
    queues |= {q for t in celery_app.tasks.values() if (q := getattr(t, "queue", None))}
    return queues


def test_supervisord_worker_consumes_every_routed_queue() -> None:
    missing = _routed_queues() - _worker_queues()
    assert not missing, f"queues routed but not consumed by the worker: {sorted(missing)}"


def test_unrouted_tasks_use_consumed_default_queue() -> None:
    assert celery_app.conf.task_default_queue == "default"


def test_maintenance_queue_consumed() -> None:
    assert "maintenance" in _worker_queues()
