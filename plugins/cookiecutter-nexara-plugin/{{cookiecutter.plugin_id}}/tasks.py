"""Celery tasks for {{cookiecutter.plugin_name}}."""

from celery import shared_task


@shared_task(name="{{cookiecutter.plugin_id}}.example_task")  # type: ignore[untyped-decorator]
def example_task() -> None:
    """Scheduled task. Replace with your logic."""
