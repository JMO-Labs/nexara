"""
@file test_repository_base.py
@brief Unit tests for the generic base repository.
"""

from unittest.mock import MagicMock

from app.models.user import User
from app.repositories.base import BaseRepository


class TestBaseRepositoryStructure:
    """@brief Verify BaseRepository class structure without database."""

    def test_is_generic_class(self):
        """BaseRepository should be a generic class."""
        assert hasattr(BaseRepository, "__class_getitem__")

    def test_base_query_exists(self):
        """BaseRepository should have a _base_query method."""
        assert callable(getattr(BaseRepository, "_base_query", None))

    def test_get_by_id_exists(self):
        assert callable(getattr(BaseRepository, "get_by_id", None))

    def test_list_exists(self):
        assert callable(getattr(BaseRepository, "list", None))

    def test_create_exists(self):
        assert callable(getattr(BaseRepository, "create", None))

    def test_update_exists(self):
        assert callable(getattr(BaseRepository, "update", None))

    def test_soft_delete_exists(self):
        assert callable(getattr(BaseRepository, "soft_delete", None))

    def test_count_exists(self):
        assert callable(getattr(BaseRepository, "count", None))


class TestSessionProperty:
    def test_session_exposes_underlying_session(self):
        class Repo(BaseRepository[User]):
            model = User

        session = MagicMock()
        assert Repo(session).session is session
