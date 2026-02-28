"""
@file post.py
@brief Pydantic schemas for posts, comments, and reactions.

Defines request/response models used by the posts API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PostAuthorResponse(BaseModel):
    """@brief Embedded author summary for post and comment responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class PostMediaResponse(BaseModel):
    """@brief Media attachment summary embedded in post responses."""

    id: UUID
    url: str
    thumbnail_url: str | None = None
    mime_type: str
    width: int | None = None
    height: int | None = None

    model_config = {"from_attributes": True}


class ReactionSummary(BaseModel):
    """@brief Aggregated reaction count for a single emoji on a post."""

    emoji: str
    count: int
    reacted_by_me: bool = False


class PostResponse(BaseModel):
    """@brief Full post object returned by the feed API."""

    id: UUID
    content: str
    author: PostAuthorResponse
    media: list[PostMediaResponse] = Field(default_factory=list)
    reactions: list[ReactionSummary] = Field(default_factory=list)
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime


class PostCreate(BaseModel):
    """
    @brief Payload for creating a new post.

    At least one of content or media_ids must be provided.
    Content may be empty for image-only posts.

    @param content Markdown content (0-10000 characters).
    @param media_ids Optional list of previously uploaded media UUIDs to attach.
    """

    content: str = Field("", max_length=10000)
    media_ids: list[UUID] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def require_content_or_media(self) -> PostCreate:
        """@brief Ensure the post has either text content or media attachments."""
        if not self.content.strip() and not self.media_ids:
            raise ValueError("Post must have content or at least one media attachment")
        return self


class PostUpdate(BaseModel):
    """
    @brief Payload for editing an existing post.

    @param content New markdown content (1-10000 characters).
    """

    content: str = Field(..., min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    """@brief Single comment in a thread."""

    id: UUID
    content: str
    author: PostAuthorResponse
    parent_id: UUID | None = None
    created_at: datetime
    replies: list[CommentResponse] = Field(default_factory=list)


class CommentCreate(BaseModel):
    """
    @brief Payload for creating a comment on a post.

    @param content Comment text (1-5000 characters).
    @param parent_id Optional parent comment UUID for nested replies.
    """

    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: UUID | None = None


class ReactionToggle(BaseModel):
    """
    @brief Payload for toggling a reaction on a post.

    @param emoji Single emoji string.
    """

    emoji: str = Field(..., min_length=1, max_length=32)


class ReactionResponse(BaseModel):
    """@brief Response after toggling a reaction."""

    action: str
    emoji: str
    count: int
