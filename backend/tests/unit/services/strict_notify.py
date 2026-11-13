"""@file strict_notify.py
@brief Test helper: a NotificationService mock that runs the real notify validation.
"""

from typing import Any
from unittest.mock import AsyncMock

from pydantic import ValidationError as PydanticValidationError

import app.services.notifications.types  # noqa: F401  (registers types)
from app.core.exceptions import AppError
from app.services.notification_service import NotificationService
from app.services.notifications import registry


async def _validate(user_id: Any, type: str, payload: dict[str, Any], actor_id: Any = None) -> None:  # noqa: A002
    try:
        t = registry.get(type)
    except KeyError:
        raise AppError(code="NOTIF_TYPE_UNKNOWN", message=type, status_code=400) from None
    try:
        t.payload_schema.model_validate(payload)
    except PydanticValidationError as exc:
        raise AppError(code="NOTIF_PREF_INVALID", message=str(exc), status_code=400) from exc


def strict_notify() -> AsyncMock:
    """@return AsyncMock(spec=NotificationService) whose notify validates like production."""
    m = AsyncMock(spec=NotificationService)
    m.notify.side_effect = _validate
    return m
