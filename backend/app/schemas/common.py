"""
@file common.py
@brief Shared Pydantic schemas for pagination, error envelopes, and common responses.

These schemas define the standard shapes used across all API endpoints.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """
    @brief Machine-readable error detail inside the error envelope.

    @param code String error code for programmatic handling.
    @param message Human-readable description.
    @param details Optional field-level details (e.g. validation errors).
    """

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """
    @brief Standard error response envelope.

    All API errors return this shape regardless of status code.
    """

    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    """
    @brief Cursor-based pagination envelope.

    Stable for real-time feeds where items are inserted frequently.
    The opaque cursor string is passed back as ``?cursor=...`` on the next request.

    @param items The page of results.
    @param next_cursor Opaque cursor string for the next page, or None.
    @param has_more Whether more results are available.
    """

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


class HealthCheck(BaseModel):
    """
    @brief Health check response schema.

    @param status Overall status — ``healthy`` or ``degraded``.
    @param version Application version string.
    @param checks Per-component health booleans.
    """

    status: str
    version: str
    checks: dict[str, bool]


class MessageResponse(BaseModel):
    """@brief Simple message-only response for operations with no resource body."""

    message: str
