"""
@file test_celery_includes.py
@brief The worker must register every core task module (thumbnails were
       "unregistered task" in production because nothing imported them).
"""

from pathlib import Path

from app.tasks.celery_app import celery_app

TASKS_DIR = Path(__file__).resolve().parents[3] / "app" / "tasks"
NOT_TASK_MODULES = {"__init__", "celery_app", "beat_lock"}


def test_every_task_module_is_included() -> None:
    modules = {
        f"app.tasks.{p.stem}" for p in TASKS_DIR.glob("*.py") if p.stem not in NOT_TASK_MODULES
    }
    assert modules <= set(celery_app.conf.include or [])


def test_media_thumbnail_task_registers_on_import() -> None:
    celery_app.loader.import_default_modules()
    assert "app.tasks.media_tasks.generate_thumbnail" in celery_app.tasks
