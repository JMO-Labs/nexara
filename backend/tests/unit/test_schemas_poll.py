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
    VoteRequest,
)


class TestPollCreate:
    """@brief Poll creation request validation."""

    def test_requires_question_and_options(self):
        """PollCreate requires question and options (min 2)."""
        req = PollCreate(
            question="What is your favorite color?",
            poll_type="single",
            options=[
                PollOptionCreate(label="Red"),
                PollOptionCreate(label="Blue"),
            ],
        )
        assert req.question == "What is your favorite color?"
        assert req.poll_type == "single"
        assert len(req.options) == 2

    def test_missing_question_rejected(self):
        with pytest.raises(ValidationError):
            PollCreate(
                poll_type="single",
                options=[
                    PollOptionCreate(label="A"),
                    PollOptionCreate(label="B"),
                ],
            )

    def test_missing_options_rejected(self):
        with pytest.raises(ValidationError):
            PollCreate(question="Q?", poll_type="single")

    def test_rejects_invalid_poll_type(self):
        """PollCreate rejects invalid poll_type values."""
        with pytest.raises(ValidationError):
            PollCreate(
                question="Q?",
                poll_type="invalid",
                options=[
                    PollOptionCreate(label="A"),
                    PollOptionCreate(label="B"),
                ],
            )

    def test_accepts_valid_poll_types(self):
        for pt in ("single", "multiple", "yes_no", "photo"):
            req = PollCreate(
                question="Q?",
                poll_type=pt,
                options=[
                    PollOptionCreate(label="A"),
                    PollOptionCreate(label="B"),
                ],
            )
            assert req.poll_type == pt

    def test_optional_fields_have_defaults(self):
        """PollCreate optional fields have defaults."""
        req = PollCreate(
            question="Q?",
            poll_type="single",
            options=[
                PollOptionCreate(label="A"),
                PollOptionCreate(label="B"),
            ],
        )
        assert req.is_anonymous is False
        assert req.expires_at is None
        assert req.result_visibility == "after_vote"


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


class TestPollResponse:
    """@brief Poll response serialization."""

    def test_serializes_from_attributes(self):
        now = datetime.now(UTC)
        resp = PollResponse(
            id=uuid4(),
            post_id=uuid4(),
            question="Favorite color?",
            poll_type="single",
            expires_at=None,
            is_anonymous=False,
            result_visibility="after_vote",
            closed=False,
            options=[],
            total_votes=0,
            user_vote=None,
            created_at=now,
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


class TestVoteRequest:
    """@brief Vote request validation."""

    def test_requires_option_ids(self):
        oid = uuid4()
        req = VoteRequest(option_ids=[oid])
        assert req.option_ids == [oid]

    def test_missing_option_ids_rejected(self):
        with pytest.raises(ValidationError):
            VoteRequest(option_ids=[])
