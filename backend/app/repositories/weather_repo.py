"""
@file weather_repo.py
@brief Saved weather places per member.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weather import WeatherPlace


class WeatherRepository:
    """@brief Data access for weather_places."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, user_id: uuid.UUID, community_id: uuid.UUID) -> list[WeatherPlace]:
        """@brief The member's places, oldest first."""
        stmt = (
            select(WeatherPlace)
            .where(WeatherPlace.user_id == user_id, WeatherPlace.community_id == community_id)
            .order_by(WeatherPlace.created_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def add(
        self, user_id: uuid.UUID, community_id: uuid.UUID, name: str, lat: float, lon: float
    ) -> WeatherPlace:
        """@brief Save a place."""
        row = WeatherPlace(user_id=user_id, community_id=community_id, name=name, lat=lat, lon=lon)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(
        self, place_id: uuid.UUID, user_id: uuid.UUID, community_id: uuid.UUID
    ) -> WeatherPlace | None:
        """@brief One of the member's places."""
        stmt = select(WeatherPlace).where(
            WeatherPlace.id == place_id,
            WeatherPlace.user_id == user_id,
            WeatherPlace.community_id == community_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete(self, place: WeatherPlace) -> None:
        """@brief Remove a place."""
        await self._session.delete(place)
        await self._session.flush()
