"""
@file nudge.py
@brief Pydantic schemas for the nudges API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NudgeResponse(BaseModel):
    """@brief A created nudge."""

    id: uuid.UUID
    sender_id: uuid.UUID
    target_id: uuid.UUID
    nudge_type: str
    created_at: datetime
