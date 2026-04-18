"""
@file interest.py
@brief Pydantic schemas for interest profiles.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InterestCategoryResponse(BaseModel):
    """@brief Interest category schema for API responses."""

    slug: str
    label: str
    description: str | None = None
    icon: str | None = None
    multi_value: bool = True
    sort_order: int = 100

    model_config = {"from_attributes": True}


class InterestCreate(BaseModel):
    """@brief Schema for creating a user interest."""

    category_slug: str
    value: str = Field(min_length=1, max_length=200)


class InterestResponse(BaseModel):
    """@brief User interest schema for API responses."""

    id: UUID
    user_id: UUID
    category_slug: str
    value: str
    source: str
    confidence: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class UserInterestsResponse(BaseModel):
    """@brief Combined interests and categories for a user."""

    interests: list[InterestResponse]
    categories: list[InterestCategoryResponse]


class InterestAnalytics(BaseModel):
    """@brief Aggregated interest count for analytics."""

    category_slug: str
    value: str
    count: int
