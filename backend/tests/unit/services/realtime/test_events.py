"""
@file test_events.py
@brief Unit tests for typed event builder functions.
"""

from __future__ import annotations

import uuid

from app.services.realtime.events import (
    CommunityTarget,
    EventType,
    FeedEvent,
    UserTarget,
    comment_created,
    post_created,
    reaction_toggled,
    typing_indicator,
    user_notification,
)


class TestPostCreated:
    """@brief Tests for the post_created builder."""

    def test_creates_feed_update_event(self):
        cid = uuid.uuid4()
        post = {"id": str(uuid.uuid4()), "content": "Hello"}
        event = post_created(CommunityTarget(community_id=cid), post)

        assert event.type == EventType.FEED_UPDATE
        assert isinstance(event.target, CommunityTarget)
        assert event.target.community_id == cid
        assert event.payload["event"] == FeedEvent.POST_CREATED
        assert event.payload["post"] == post


class TestCommentCreated:
    """@brief Tests for the comment_created builder."""

    def test_creates_comment_event(self):
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        uid = uuid.uuid4()
        comment = {"id": str(uuid.uuid4()), "content": "Nice!"}
        event = comment_created(CommunityTarget(community_id=cid), pid, comment, uid)

        assert event.type == EventType.FEED_UPDATE
        assert isinstance(event.target, CommunityTarget)
        assert event.payload["event"] == FeedEvent.COMMENT_CREATED
        assert event.payload["post_id"] == str(pid)
        assert event.payload["comment"] == comment
        assert event.payload["user_id"] == str(uid)


class TestReactionToggled:
    """@brief Tests for the reaction_toggled builder."""

    def test_creates_reaction_event(self):
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        tid = uuid.uuid4()
        uid = uuid.uuid4()
        event = reaction_toggled(
            CommunityTarget(community_id=cid), pid, "post", tid, "heart", 5, "added", uid
        )

        assert event.type == EventType.FEED_UPDATE
        assert event.payload["event"] == FeedEvent.REACTION_TOGGLED
        assert event.payload["post_id"] == str(pid)
        assert event.payload["target_type"] == "post"
        assert event.payload["target_id"] == str(tid)
        assert event.payload["emoji"] == "heart"
        assert event.payload["count"] == 5
        assert event.payload["action"] == "added"


class TestUserNotification:
    """@brief Tests for the user_notification builder."""

    def test_creates_notification_event(self):
        uid = uuid.uuid4()
        nid = uuid.uuid4()
        event = user_notification(uid, nid, "mention", {"msg": "hi"}, "2026-01-01T00:00:00")

        assert event.type == EventType.NOTIFICATION
        assert isinstance(event.target, UserTarget)
        assert event.target.user_id == uid
        assert event.payload["id"] == str(nid)
        assert event.payload["type"] == "mention"
        assert event.payload["payload"] == {"msg": "hi"}
        assert event.payload["created_at"] == "2026-01-01T00:00:00"


class TestTypingIndicator:
    """@brief Tests for the typing_indicator builder."""

    def test_creates_typing_event(self):
        cid = uuid.uuid4()
        uid = uuid.uuid4()
        event = typing_indicator(cid, uid)

        assert event.type == EventType.TYPING
        assert isinstance(event.target, CommunityTarget)
        assert event.target.community_id == cid
        assert event.payload["user_id"] == str(uid)
