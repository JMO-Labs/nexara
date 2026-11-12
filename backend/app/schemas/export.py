"""
@file export.py
@brief Pydantic schemas for the personal data export API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportRequestResponse(BaseModel):
    """@brief Response to a new export request."""

    export_id: uuid.UUID
    status: str
    created_at: datetime


class ExportStatus(BaseModel):
    """@brief Export status; status ∈ {pending, processing, ready, failed, expired}."""

    export_id: uuid.UUID
    status: str
    created_at: datetime
    ready_at: datetime | None
    expires_at: datetime | None
    file_size_bytes: int | None
    download_url: str | None
