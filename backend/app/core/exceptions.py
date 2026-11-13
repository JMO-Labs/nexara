"""
@file exceptions.py
@brief Custom exception classes and FastAPI exception handlers.

All application errors follow a consistent JSON shape::

    {
      "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable description",
        "details": { ... }
      }
    }

Error codes are string constants so the frontend can handle specific errors
without string-matching on messages.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.i18n import _

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """
    @brief Base application error.

    All domain-specific exceptions inherit from this so that a single
    handler can catch them and format the standard error envelope.

    @param code Machine-readable error code string.
    @param message Human-readable error description.
    @param status_code HTTP status code to return.
    @param details Optional dict with extra context (field-level errors, etc.).
    """

    def __init__(
        self,
        code: str = "INTERNAL_ERROR",
        message: str = "",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or _("An unexpected error occurred")
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppError):
    """@brief Raised when authentication credentials are invalid or expired."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message or _("Invalid or expired credentials"),
            status_code=401,
            details=details,
        )


class AuthorizationError(AppError):
    """@brief Raised when the user lacks the required role or permission."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message or _("Insufficient permissions"),
            status_code=403,
            details=details,
        )


class NotFoundError(AppError):
    """@brief Raised when a requested resource does not exist."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=message or _("Resource not found"),
            status_code=404,
            details=details,
        )


class GoneError(AppError):
    """@brief Raised when a resource existed but is no longer available (e.g. expired)."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="GONE",
            message=message or _("Resource is no longer available"),
            status_code=410,
            details=details,
        )


class ConflictError(AppError):
    """@brief Raised on duplicate resource creation (email, username, etc.)."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="CONFLICT",
            message=message or _("Resource already exists"),
            status_code=409,
            details=details,
        )


class ValidationError(AppError):
    """@brief Raised when a field value fails business-rule validation (422)."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message or _("Invalid value"),
            status_code=422,
            details=details,
        )


class RateLimitError(AppError):
    """@brief Raised when a client exceeds the rate limit."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message=message or _("Too many requests — please try again later"),
            status_code=429,
            details=details,
        )


class StorageError(AppError):
    """@brief Raised when the storage backend (S3/local FS) is unavailable."""

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="STORAGE_ERROR",
            message=message or _("Storage service unavailable"),
            status_code=503,
            details=details,
        )


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """@brief Build the standard error envelope dict."""
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """@brief Handle all AppError subclasses with the standard envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """@brief Reformat Pydantic validation errors into the standard envelope."""
    details = {}
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        details[field] = err["msg"]
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", _("Request validation failed"), details),
    )


async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """@brief Catch-all for unhandled exceptions — logs full traceback."""
    logger.exception(
        "unhandled_exception",
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", _("An unexpected error occurred")),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    @brief Register all exception handlers on the FastAPI application.

    Called during app factory setup in ``main.py``.

    @param app The FastAPI application instance.
    """
    # third-party signature is wider than its stub
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    # third-party signature is wider than its stub
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_error_handler)
