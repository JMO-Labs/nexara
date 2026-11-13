"""
@file webhook.py
@brief Pydantic schemas for webhook subscription endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

WebhookUrl = Annotated[str, Field(min_length=8, max_length=2048, pattern=r"^https?://\S+$")]


class WebhookCreateRequest(BaseModel):
    """@brief Create body; empty ``type_keys`` subscribes to all types."""

    url: WebhookUrl
    type_keys: list[str] = Field(default_factory=list, max_length=50)


class WebhookUpdateRequest(BaseModel):
    """@brief Partial update body."""

    url: WebhookUrl | None = None
    type_keys: list[str] | None = Field(default=None, max_length=50)
    enabled: bool | None = None


class WebhookListItem(BaseModel):
    """@brief Subscription view; never includes the secret."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    type_keys: list[str]
    enabled: bool
    failure_count: int
    last_failure_at: datetime | None
    created_at: datetime


class WebhookCreateResponse(WebhookListItem):
    """@brief Create response; ``secret`` is revealed only here, once."""

    secret: str
