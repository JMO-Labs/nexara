"""
@file service.py
@brief Weather board: the viewer's saved places, their own city and their
       pinned people's cities. A member's city is used only when their
       profile location is visible to the viewer, and only at city
       precision (rounded coordinates, city label, never the raw text).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.core.i18n import _
from app.models.user import User
from app.repositories.weather_repo import WeatherRepository
from app.services.weather.provider import WeatherProvider

MAX_PLACES = 8
MAX_PEOPLE = 12


class WeatherService:
    """@brief Saved places plus a privacy-aware weather board."""

    def __init__(
        self,
        repo: WeatherRepository,
        provider: WeatherProvider,
        community_id: uuid.UUID,
        *,
        profiles: Any,
        favorites: Any,
    ) -> None:
        """
        @param profiles object with ``view(user_id, viewer)`` (ProfileService)
        @param favorites async callable ``(viewer_id) -> list[uuid]`` (pinned people)
        """
        self._repo = repo
        self._provider = provider
        self._community_id = community_id
        self._profiles = profiles
        self._favorites = favorites

    async def places(self, user: User) -> list[Any]:
        """@brief The member's saved places."""
        return await self._repo.list(user.id, self._community_id)

    async def add_place(self, user: User, name: str, lat: float, lon: float) -> Any:
        """@brief Save a place (max 8)."""
        if len(await self._repo.list(user.id, self._community_id)) >= MAX_PLACES:
            raise ValidationError(message=_("You can save up to 8 places"))
        return await self._repo.add(
            user.id, self._community_id, name.strip(), round(lat, 3), round(lon, 3)
        )

    async def remove_place(self, user: User, place_id: uuid.UUID) -> None:
        """@brief Delete one of the member's places."""
        place = await self._repo.get(place_id, user.id, self._community_id)
        if place is None:
            raise NotFoundError(message=_("Place not found"))
        await self._repo.delete(place)

    async def forecast(self, lat: float, lon: float) -> dict[str, Any] | None:
        """@brief Forecast for any coordinates (event pages)."""
        return await self._provider.forecast(lat, lon)

    async def _person(self, user_id: uuid.UUID, viewer: User) -> dict[str, Any] | None:
        try:
            p = await self._profiles.view(user_id, viewer)
        except NotFoundError:
            return None
        if not p.location:
            return None
        city = await self._provider.geocode_city(p.location)
        if city is None:
            return None
        return {
            "id": str(p.id),
            "kind": "self" if p.id == viewer.id else "person",
            "label": p.display_name,
            "place": city["label"],
            "lat": city["lat"],
            "lon": city["lon"],
            "user_id": p.id,
            "avatar_url": p.avatar_url,
        }

    async def board(self, viewer: User) -> list[dict[str, Any]]:
        """
        @brief Self, saved places, then pinned people, each with a forecast
               (null when the provider is unreachable).
        """
        people_ids = [viewer.id, *(await self._favorites(viewer.id))[:MAX_PEOPLE]]
        people = [await self._person(uid, viewer) for uid in dict.fromkeys(people_ids)]
        places = [
            {
                "id": str(pl.id),
                "kind": "place",
                "label": pl.name,
                "place": None,
                "lat": pl.lat,
                "lon": pl.lon,
                "user_id": None,
                "avatar_url": None,
            }
            for pl in await self._repo.list(viewer.id, self._community_id)
        ]
        items = [*(p for p in people[:1] if p), *places, *(p for p in people[1:] if p)]
        forecasts = await asyncio.gather(
            *(self._provider.forecast(i["lat"], i["lon"]) for i in items)
        )
        for item, fc in zip(items, forecasts, strict=True):
            item["forecast"] = fc
        return items
