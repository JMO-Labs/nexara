"""
@file recap.py
@brief Recap email unsubscribe (token-authenticated, no login).
"""

from __future__ import annotations

import uuid
from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import AppError
from app.core.i18n import _
from app.core.security import decode_token
from app.repositories.settings_repo import SettingsRepository

router = APIRouter(prefix="/recap", tags=["recap"])

UNSUB_PURPOSE = "recap_unsub"


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title></head>"
        '<body style="font-family: system-ui, sans-serif; font-size: 18px; '
        'max-width: 32rem; margin: 3rem auto; padding: 0 1rem; color: #222;">'
        f"<main><h1>{escape(title)}</h1><p>{escape(body)}</p></main></body></html>"
    )


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """@brief Turn the recap email off for the token's user (400 on a bad/expired token)."""
    try:
        user_id = uuid.UUID(decode_token(token, expected_type=UNSUB_PURPOSE)["sub"])
    except ValueError:
        raise AppError(
            "INVALID_TOKEN", _("This unsubscribe link is invalid or has expired"), 400
        ) from None
    repo = SettingsRepository(db)
    if await repo.get_by_user_id(user_id) is not None:
        await repo.update(user_id, {"recap_cadence": "off"})
    return _page(
        _("You are unsubscribed"),
        _("You will no longer get the family recap email. You can turn it back on in settings."),
    )
