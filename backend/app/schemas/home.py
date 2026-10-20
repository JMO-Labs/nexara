"""
@file home.py
@brief Pydantic schemas for the home aggregation endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel


class HomeSummaryResponse(BaseModel):
    """
    @brief Response for GET /api/v1/home/summary.

    @param new_posts Count of posts visible to user since last visit.
    @param upcoming_events Count of events in the next 7 days.
    @param unread_notifications Count of unread in-app notifications.
    """

    new_posts: int
    upcoming_events: int
    unread_notifications: int
