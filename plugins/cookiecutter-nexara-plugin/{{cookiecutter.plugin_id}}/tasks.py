"""Celery tasks for {{cookiecutter.plugin_name}}."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="{{cookiecutter.plugin_id}}.example_task")
def example_task() -> None:
    """Scheduled task. Replace with your logic."""
