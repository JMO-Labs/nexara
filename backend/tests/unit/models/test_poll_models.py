"""
@file test_poll_models.py
@brief Unit tests for Poll, PollOption, PollVote model structure.
"""

import app.models  # noqa: F401
from app.models.poll import Poll, PollOption, PollVote


class TestPollModel:
    """@brief Verify the Poll model schema."""

    def test_tablename(self):
        """Poll table name should be polls."""
        assert Poll.__tablename__ == "polls"

    def test_has_required_columns(self):
        """Poll should have all required columns."""
        cols = {c.name for c in Poll.__table__.columns}
        required = {
            "id",
            "community_id",
            "post_id",
            "created_by",
            "poll_type",
            "question",
            "expires_at",
            "is_anonymous",
            "allow_add_options",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert required.issubset(cols)


class TestPollOptionModel:
    """@brief Verify the PollOption model schema."""

    def test_tablename(self):
        """PollOption table name should be poll_options."""
        assert PollOption.__tablename__ == "poll_options"

    def test_has_required_columns(self):
        """PollOption should have all required columns."""
        cols = {c.name for c in PollOption.__table__.columns}
        required = {
            "id",
            "poll_id",
            "label",
            "image_media_id",
            "position",
            "created_at",
        }
        assert required.issubset(cols)


class TestPollVoteModel:
    """@brief Verify the PollVote model schema."""

    def test_tablename(self):
        """PollVote table name should be poll_votes."""
        assert PollVote.__tablename__ == "poll_votes"

    def test_has_required_columns(self):
        """PollVote should have all required columns."""
        cols = {c.name for c in PollVote.__table__.columns}
        required = {
            "id",
            "poll_id",
            "option_id",
            "user_id",
            "created_at",
        }
        assert required.issubset(cols)
