"""
@file celebration.py
@brief Calendar celebrations: birthdays (people and pets) and gotcha days.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel


class CalendarCelebration(BaseModel):
    """@brief One all-day celebration on the calendar."""

    date: date
    occasion: Literal["birthday", "gotcha_day", "remembrance"]
    subject_type: Literal["user", "household"]
    subject_id: uuid.UUID
    name: str
    is_pet: bool = False
    link: str
    title: str | None = None  # set for remembrance: "Remembering <name>"
