"""
@file test_weather.py
@brief Weather provider shaping/caching/failure and board privacy rules.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.repositories.weather_repo import WeatherRepository
from app.services.weather.provider import WeatherProvider
from app.services.weather.service import WeatherService

OM = {
    "current": {"temperature_2m": 21.5, "weather_code": 2, "is_day": 0},
    "daily": {
        "time": ["2026-11-21", "2026-11-22"],
        "weather_code": [2, 61],
        "temperature_2m_max": [24.0, 18.0],
        "temperature_2m_min": [10.0, 9.0],
        "precipitation_probability_max": [0, 80],
    },
}
PHOTON = {
    "features": [
        {
            "geometry": {"coordinates": [-111.8315, 33.4152]},
            "properties": {"name": "Mesa", "city": "Mesa", "state": "Arizona"},
        }
    ]
}


class FakeCache(dict[str, str]):
    async def get(self, k: str) -> str | None:
        return dict.get(self, k)

    async def setex(self, k: str, ttl: int, v: str) -> None:
        self[k] = v


def _provider(calls: list[httpx.Request], fail: bool = False) -> WeatherProvider:
    def handle(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if fail:
            return httpx.Response(503)
        body = PHOTON if "photon" in req.url.host else OM
        return httpx.Response(200, json=body)

    return WeatherProvider(FakeCache(), transport=httpx.MockTransport(handle))  # type: ignore[arg-type]


async def test_forecast_shapes_and_caches():
    calls: list[httpx.Request] = []
    p = _provider(calls)
    fc = await p.forecast(33.41523, -111.83151)
    assert fc is not None
    assert fc["current"] == {"temp_c": 21.5, "code": 2, "is_day": False}
    assert fc["daily"][1] == {
        "date": "2026-11-22",
        "code": 61,
        "max_c": 18.0,
        "min_c": 9.0,
        "precip": 80,
    }
    assert calls[0].url.params["latitude"] == "33.42"
    await p.forecast(33.4199, -111.8301)  # same rounded cell
    assert len(calls) == 1


async def test_provider_failure_returns_none():
    p = _provider([], fail=True)
    assert await p.forecast(1, 2) is None
    assert await p.geocode_city("Mesa, AZ") is None


async def test_geocode_rounds_to_city_precision_and_sends_only_text():
    calls: list[httpx.Request] = []
    city = await _provider(calls).geocode_city("  Mesa,   AZ ")
    assert city == {"label": "Mesa, Arizona", "lat": 33.4, "lon": -111.8}
    assert calls[0].url.params["q"] == "Mesa, AZ"
    assert "User-Agent" in calls[0].headers and "@" not in calls[0].headers["User-Agent"]


def _viewer() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    return u


def _svc(profiles: dict[uuid.UUID, object], favorites: list[uuid.UUID]) -> WeatherService:
    repo = AsyncMock(spec=WeatherRepository)
    repo.list.return_value = [SimpleNamespace(id=uuid.uuid4(), name="Cabin", lat=44.1, lon=-73.9)]
    provider = AsyncMock(spec=WeatherProvider)
    provider.geocode_city.side_effect = lambda t: {"label": t.title(), "lat": 1.0, "lon": 2.0}
    provider.forecast.return_value = {"current": {}, "daily": []}

    async def view(uid: uuid.UUID, viewer: object) -> object:
        p = profiles.get(uid)
        if p is None:
            raise NotFoundError(message="x")
        return p

    return WeatherService(
        repo,
        provider,
        uuid.uuid4(),
        profiles=SimpleNamespace(view=view),
        favorites=AsyncMock(return_value=favorites),
    )


def _profile(uid: uuid.UUID, location: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=uid, display_name="P", avatar_url=None, location=location)


async def test_board_uses_only_visible_locations_in_order():
    me = _viewer()
    shown, hidden, blocked = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    svc = _svc(
        {
            me.id: _profile(me.id, "mesa"),
            shown: _profile(shown, "phoenix"),
            hidden: _profile(hidden, None),
        },
        [shown, hidden, blocked],
    )
    board = await svc.board(me)
    assert [(b["kind"], b["place"]) for b in board] == [
        ("self", "Mesa"),
        ("place", None),
        ("person", "Phoenix"),
    ]
    assert all(b["forecast"] is not None for b in board)


async def test_place_limit():
    svc = _svc({}, [])
    svc._repo.list.return_value = [MagicMock()] * 8  # type: ignore[attr-defined]
    with pytest.raises(ValidationError):
        await svc.add_place(_viewer(), "X", 1, 2)


