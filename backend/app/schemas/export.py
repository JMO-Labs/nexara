"""
@file export.py
@brief Pydantic schemas for the data export API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportRequested(BaseModel):
    """@brief Response to a new export request."""

    export_id: uuid.UUID
    status: str
    created_at: datetime


class ExportStatus(BaseModel):
    """@brief Export state; ``download_url`` only when ready and unexpired."""

    export_id: uuid.UUID
    status: str
    created_at: datetime
    ready_at: datetime | None = None
    expires_at: datetime | None = None
    file_size_bytes: int | None = None
    download_url: str | None = None
