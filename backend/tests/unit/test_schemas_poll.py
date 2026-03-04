"""
@file test_schemas_poll.py
@brief Unit tests for poll Pydantic schemas: validation rules, field constraints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.poll import (
    PollCreate,
    PollOptionCreate,
    PollOptionResponse,
    PollResponse,
    PollVoteCreate,
)


class TestPollCreate:
    """@brief Poll creation request validation."""

    def test_requires_question_and_poll_type(self):
        """PollCreate requires question and poll_type."""
        req = PollCreate(question="What is your favorite color?", poll_type="single")
        assert req.question == "What is your favorite color?"
        assert req.poll_type == "single"

    def test_missing_question_rejected(self):
        with pytest.raises(ValidationError):
            PollCreate(poll_type="single")

    def test_missing_poll_type_rejected(self):
        with pytest.raises(ValidationError):
            PollCreate(question="Question?")

    def test_rejects_invalid_poll_type(self):
        """PollCreate rejects invalid poll_type values."""
        with pytest.raises(ValidationError):
            PollCreate(question="Q?", poll_type="invalid")

    def test_accepts_valid_poll_types(self):
        for pt in ("single", "multiple", "yes_no", "photo"):
            req = PollCreate(question="Q?", poll_type=pt)
            assert req.poll_type == pt

    def test_optional_fields_have_defaults(self):
        """PollCreate optional fields have defaults (is_anonymous=False, etc.)."""
        req = PollCreate(question="Q?", poll_type="single")
        assert req.is_anonymous is False
        assert req.allow_add_options is False
        assert req.expires_at is None
        assert req.options == []


class TestPollOptionCreate:
    """@brief Poll option creation validation."""

    def test_requires_label(self):
        req = PollOptionCreate(label="Option A")
        assert req.label == "Option A"

    def test_missing_label_rejected(self):
        with pytest.raises(ValidationError):
            PollOptionCreate()

    def test_optional_fields_defaults(self):
        req = PollOptionCreate(label="Option")
        assert req.image_media_id is None
        assert req.position == 0


class TestPollResponse:
    """@brief Poll response serialization from model attributes."""

    def test_serializes_from_attributes(self):
        now = datetime.now(UTC)
        resp = PollResponse(
            id=uuid4(),
            question="Favorite color?",
            poll_type="single",
            expires_at=None,
            is_anonymous=False,
            allow_add_options=False,
            created_by=uuid4(),
            options=[],
            total_votes=0,
            created_at=now,
            updated_at=now,
        )
        assert resp.question == "Favorite color?"
        assert resp.total_votes == 0
        assert resp.options == []


class TestPollOptionResponse:
    """@brief Poll option response serialization."""

    def test_serializes_from_attributes(self):
        resp = PollOptionResponse(
            id=uuid4(),
            label="Red",
            image_media_id=None,
            position=0,
            vote_count=5,
        )
        assert resp.label == "Red"
        assert resp.vote_count == 5


class TestPollVoteCreate:
    """@brief Poll vote creation validation."""

    def test_requires_poll_id_and_option_id(self):
        pid = uuid4()
        oid = uuid4()
        req = PollVoteCreate(poll_id=pid, option_id=oid)
        assert req.poll_id == pid
        assert req.option_id == oid

    def test_missing_poll_id_rejected(self):
        with pytest.raises(ValidationError):
            PollVoteCreate(option_id=uuid4())

    def test_missing_option_id_rejected(self):
        with pytest.raises(ValidationError):
            PollVoteCreate(poll_id=uuid4())
