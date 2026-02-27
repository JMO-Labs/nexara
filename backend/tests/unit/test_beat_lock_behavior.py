"""
@file test_beat_lock_behavior.py
@brief Unit tests for beat_lock advisory lock behavior with mocked psycopg2.

Tests verify the advisory lock function calls the correct SQL and handles
connection failures appropriately.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tasks.beat_lock import BEAT_LOCK_ID, acquire_beat_lock


class TestAcquireBeatLock:
    """@brief Advisory lock acquisition tests with mocked database."""

    @patch("app.tasks.beat_lock.psycopg2.connect")
    def test_acquires_lock_with_correct_id(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = acquire_beat_lock("postgresql://user:pass@localhost/db")

        assert result is True
        mock_connect.assert_called_once_with("postgresql://user:pass@localhost/db")
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "SELECT pg_advisory_lock(%s)", (BEAT_LOCK_ID,),
        )

    @patch("app.tasks.beat_lock.psycopg2.connect")
    def test_sets_autocommit(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = MagicMock()

        acquire_beat_lock("postgresql://user:pass@localhost/db")

        assert mock_conn.autocommit is True

    @patch("app.tasks.beat_lock.psycopg2.connect")
    def test_connection_failure_raises(self, mock_connect):
        import psycopg2
        mock_connect.side_effect = psycopg2.OperationalError("connection refused")

        with pytest.raises(psycopg2.OperationalError):
            acquire_beat_lock("postgresql://bad:bad@nowhere/db")

    def test_lock_id_is_0xBEA7(self):
        assert BEAT_LOCK_ID == 0xBEA7

    def test_lock_id_is_integer(self):
        assert isinstance(BEAT_LOCK_ID, int)
