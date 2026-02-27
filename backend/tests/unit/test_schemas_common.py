"""
@file test_schemas_common.py
@brief Unit tests for shared Pydantic schemas.
"""

from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthCheck,
    MessageResponse,
    PaginatedResponse,
)


class TestErrorResponse:
    """@brief Verify error envelope serialization."""

    def test_minimal_error(self):
        resp = ErrorResponse(
            error=ErrorDetail(code="NOT_FOUND", message="Not found")
        )
        data = resp.model_dump()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["message"] == "Not found"
        assert data["error"]["details"] == {}

    def test_error_with_details(self):
        resp = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Validation failed",
                details={"email": "Invalid format"},
            )
        )
        assert resp.error.details["email"] == "Invalid format"


class TestPaginatedResponse:
    """@brief Verify cursor-based pagination schema."""

    def test_empty_page(self):
        page = PaginatedResponse[str](items=[], next_cursor=None, has_more=False)
        data = page.model_dump()
        assert data["items"] == []
        assert data["has_more"] is False

    def test_page_with_cursor(self):
        page = PaginatedResponse[int](items=[1, 2, 3], next_cursor="abc123", has_more=True)
        assert page.has_more is True
        assert page.next_cursor == "abc123"
        assert len(page.items) == 3


class TestHealthCheck:
    """@brief Verify health check response schema."""

    def test_healthy(self):
        hc = HealthCheck(
            status="healthy",
            version="0.1.0",
            checks={"db": True, "redis": True, "storage": True},
        )
        assert hc.status == "healthy"
        assert hc.checks["db"] is True

    def test_degraded(self):
        hc = HealthCheck(
            status="degraded",
            version="0.1.0",
            checks={"db": True, "redis": False, "storage": True},
        )
        assert hc.status == "degraded"


class TestMessageResponse:
    """@brief Verify simple message response."""

    def test_message(self):
        msg = MessageResponse(message="Done")
        assert msg.message == "Done"
