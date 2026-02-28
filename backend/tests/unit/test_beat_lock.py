"""
@file test_beat_lock.py
@brief Unit tests for the Beat advisory lock module.
"""

from app.tasks.beat_lock import BEAT_LOCK_ID


class TestBeatLockConstants:
    """@brief Verify Beat lock constants."""

    def test_lock_id_is_stable(self):
        """The lock ID must remain constant across versions."""
        assert BEAT_LOCK_ID == 0xBEA7

    def test_lock_id_is_integer(self):
        assert isinstance(BEAT_LOCK_ID, int)
