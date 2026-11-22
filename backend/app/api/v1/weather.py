"""
@file weather.py
@brief Weather: saved places, the weather board and a coordinate forecast
       (proxied and cached server-side).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import limiter
from app.core.valkey import DB_CACHE, get_pool
from app.models.user import User
from app.repositories.home_people_repo import HomePeopleRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.weather_repo import WeatherRepository
from app.schemas.common import MessageResponse
from app.schemas.weather import BoardItem, Forecast, PlaceCreate, PlaceResponse
from app.services.profiles.service import ProfileService
from app.services.weather.provider import WeatherProvider
from app.services.weather.service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


def _service(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> WeatherService:
    """@brief WeatherService bound to the request session and cache."""
    return WeatherService(
        WeatherRepository(db),
        WeatherProvider(get_pool(get_settings(), DB_CACHE)),
        user.community_id,
        profiles=ProfileService(ProfileRepository(db), user.community_id),
        favorites=HomePeopleRepository(db).favorites,
    )


@router.get("/board", response_model=list[BoardItem])
async def board(
    user: User = Depends(get_current_user), svc: WeatherService = Depends(_service)
) -> Any:
    """@brief Weather for your city, saved places and pinned people."""
    return await svc.board(user)


@router.get("/forecast", response_model=Forecast | None)
@limiter.limit("60/minute")
async def forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    svc: WeatherService = Depends(_service),
) -> Any:
    """@brief Forecast for coordinates (null when unavailable)."""
    return await svc.forecast(lat, lon)


@router.get("/places", response_model=list[PlaceResponse])
async def list_places(
    user: User = Depends(get_current_user), svc: WeatherService = Depends(_service)
) -> Any:
    """@brief Your saved places."""
    return await svc.places(user)


@router.post("/places", response_model=PlaceResponse, status_code=201)
async def add_place(
    body: PlaceCreate,
    user: User = Depends(get_current_user),
    svc: WeatherService = Depends(_service),
) -> Any:
    """@brief Save a place."""
    return await svc.add_place(user, body.name, body.lat, body.lon)


@router.delete("/places/{place_id}", response_model=MessageResponse)
async def remove_place(
    place_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: WeatherService = Depends(_service),
) -> MessageResponse:
    """@brief Remove a saved place."""
    await svc.remove_place(user, place_id)
    return MessageResponse(message="Removed")
