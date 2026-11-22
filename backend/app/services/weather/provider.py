"""
@file provider.py
@brief Server-side proxy for keyless weather and geocoding providers:
       Open-Meteo forecasts and Photon (Komoot) place lookup. Results are
       cached in Valkey so browsers never contact the providers and
       repeated views cost nothing. Only coordinates or a place name are
       sent; never who is asking.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from redis.asyncio import Redis

from app.core.cache import cache_get, cache_set

logger = structlog.get_logger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PHOTON_URL = "https://photon.komoot.io/api"
UA = "Nexara/1.0 (self-hosted community app)"
FORECAST_TTL = 30 * 60
GEOCODE_TTL = 30 * 24 * 3600
MISS_TTL = 24 * 3600


def _shape(data: dict[str, Any]) -> dict[str, Any]:
    """@brief Open-Meteo response -> compact {current, daily[]} in Celsius."""
    cur = data.get("current") or {}
    d = data.get("daily") or {}

    def at(name: str, i: int) -> Any:
        col = d.get(name) or []
        return col[i] if i < len(col) else None

    days = [
        {
            "date": day,
            "code": at("weather_code", i),
            "max_c": at("temperature_2m_max", i),
            "min_c": at("temperature_2m_min", i),
            "precip": at("precipitation_probability_max", i),
        }
        for i, day in enumerate(d.get("time") or [])
    ]
    return {
        "current": {
            "temp_c": cur.get("temperature_2m"),
            "code": cur.get("weather_code"),
            "is_day": bool(cur.get("is_day", 1)),
        },
        "daily": days,
    }


class WeatherProvider:
    """@brief Cached Open-Meteo / Photon client."""

    def __init__(self, cache: Redis | None, transport: httpx.AsyncBaseTransport | None = None):
        self._cache = cache
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=8.0, trust_env=False, headers={"User-Agent": UA}, transport=self._transport
        )

    async def _cached(self, key: str) -> Any:
        raw = await cache_get(self._cache, key) if self._cache is not None else None
        return json.loads(raw) if raw else None

    async def _store(self, key: str, value: Any, ttl: int) -> None:
        if self._cache is not None:
            await cache_set(self._cache, key, json.dumps(value), ttl)

    async def forecast(self, lat: float, lon: float) -> dict[str, Any] | None:
        """
        @brief Current conditions and a 16-day daily forecast.
        @return shaped forecast, or None when the provider is unreachable
        """
        lat, lon = round(lat, 2), round(lon, 2)
        key = f"wx:fc:{lat}:{lon}"
        if (hit := await self._cached(key)) is not None:
            return dict(hit)
        params: dict[str, str | float | int] = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 16,
        }
        try:
            async with self._client() as c:
                r = await c.get(FORECAST_URL, params=params)
                r.raise_for_status()
                out = _shape(r.json())
        except (httpx.HTTPError, ValueError, TypeError):
            logger.warning("weather_forecast_failed", lat=lat, lon=lon)
            return None
        await self._store(key, out, FORECAST_TTL)
        return out

    async def geocode_city(self, text: str) -> dict[str, Any] | None:
        """
        @brief Place name -> {label, lat, lon} rounded to ~11 km (city level).
        @return None when nothing matches or the provider is unreachable
        """
        q = " ".join(text.split())[:120]
        if not q:
            return None
        key = f"wx:geo:{q.lower()}"
        if (hit := await self._cached(key)) is not None:
            return dict(hit) if hit else None
        try:
            async with self._client() as c:
                r = await c.get(PHOTON_URL, params={"q": q, "limit": 1, "lang": "en"})
                r.raise_for_status()
                feats = r.json().get("features") or []
        except (httpx.HTTPError, ValueError):
            logger.warning("weather_geocode_failed")
            return None
        if not feats:
            await self._store(key, {}, MISS_TTL)
            return None
        lon, lat = feats[0]["geometry"]["coordinates"][:2]
        p = feats[0].get("properties") or {}
        city = p.get("city") or p.get("name") or q
        label = ", ".join(x for x in (city, p.get("state")) if x)
        out = {"label": label, "lat": round(float(lat), 1), "lon": round(float(lon), 1)}
        await self._store(key, out, GEOCODE_TTL)
        return out
