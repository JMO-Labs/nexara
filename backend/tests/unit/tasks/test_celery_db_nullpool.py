"""
@file test_celery_db_nullpool.py
@brief Worker processes bind the shared session factory to a NullPool engine.
"""

from sqlalchemy.pool import NullPool

from app.db.session import async_session_factory, engine
from app.tasks.celery_app import _per_task_db_connections


def test_worker_init_rebinds_session_factory_to_nullpool() -> None:
    original = async_session_factory.kw["bind"]
    try:
        _per_task_db_connections()
        bound = async_session_factory.kw["bind"]
        assert isinstance(bound.pool, NullPool)
        assert bound is not engine
    finally:
        async_session_factory.configure(bind=original)
