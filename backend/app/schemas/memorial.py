"""
@file memorial.py
@brief Request bodies for memorial endpoints.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PassedOnBody(BaseModel):
    """@brief Optional passed-on date (null clears / leaves it unset)."""

    passed_on: date | None = None
