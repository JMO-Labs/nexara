"""
@file test_db_base.py
@brief Unit tests for the SQLAlchemy base model and mixins.
"""

from sqlalchemy import inspect

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SampleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """@brief Minimal model for testing mixins."""

    __tablename__ = "test_sample"


class TestBase:
    """@brief Verify Base and mixin behavior."""

    def test_base_has_metadata(self):
        """@brief Base.metadata should exist for Alembic."""
        assert Base.metadata is not None

    def test_uuid_pk_mixin_column_exists(self):
        """@brief UUIDPrimaryKeyMixin should add an 'id' column."""
        mapper = inspect(SampleModel)
        column_names = [c.key for c in mapper.columns]
        assert "id" in column_names

    def test_uuid_pk_is_primary_key(self):
        """@brief The 'id' column should be a primary key."""
        mapper = inspect(SampleModel)
        pk_cols = [c.name for c in mapper.primary_key]
        assert "id" in pk_cols

    def test_timestamp_mixin_created_at(self):
        """@brief TimestampMixin should add 'created_at'."""
        mapper = inspect(SampleModel)
        column_names = [c.key for c in mapper.columns]
        assert "created_at" in column_names

    def test_timestamp_mixin_updated_at(self):
        """@brief TimestampMixin should add 'updated_at'."""
        mapper = inspect(SampleModel)
        column_names = [c.key for c in mapper.columns]
        assert "updated_at" in column_names

    def test_id_column_type_is_uuid(self):
        """@brief The 'id' column should use the PostgreSQL UUID type."""
        mapper = inspect(SampleModel)
        id_col = mapper.columns["id"]
        assert "UUID" in str(id_col.type)
