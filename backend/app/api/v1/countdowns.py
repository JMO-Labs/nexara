"""
@file countdowns.py
@brief Countdown routes: CRUD, follow, Home list and browse.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_current_user
from app.core.deps_countdown import get_countdown_service
from app.models.user import User
from app.schemas.countdown import CountdownCreate, CountdownResponse, CountdownUpdate
from app.services.countdown_service import CountdownService

router = APIRouter(prefix="/countdowns", tags=["countdowns"])


@router.post("", response_model=CountdownResponse, status_code=status.HTTP_201_CREATED)
async def create_countdown(
    body: CountdownCreate,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> CountdownResponse:
    """@brief Create a countdown and its feed card."""
    return await svc.create(user, body)


@router.get("/following", response_model=list[CountdownResponse])
async def list_following(
    include_done: bool = False,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> list[CountdownResponse]:
    """@brief Followed countdowns for Home, soonest first."""
    return await svc.list_following(user, include_done)


@router.get("", response_model=list[CountdownResponse])
async def list_countdowns(
    scope: str = "all",
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> list[CountdownResponse]:
    """@brief Browse every countdown the viewer may see."""
    return await svc.list_all(user)


@router.get("/{countdown_id}", response_model=CountdownResponse)
async def get_countdown(
    countdown_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> CountdownResponse:
    """@brief One countdown (404 if not visible)."""
    return await svc.get(user, countdown_id)


@router.patch("/{countdown_id}", response_model=CountdownResponse)
async def update_countdown(
    countdown_id: uuid.UUID,
    body: CountdownUpdate,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> CountdownResponse:
    """@brief Edit (author only)."""
    return await svc.update(user, countdown_id, body)


@router.delete("/{countdown_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_countdown(
    countdown_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> Response:
    """@brief Delete (author or admin); removes the feed post too."""
    await svc.delete(user, countdown_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{countdown_id}/follow", response_model=CountdownResponse)
async def follow_countdown(
    countdown_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> CountdownResponse:
    """@brief Follow a countdown."""
    return await svc.follow(user, countdown_id, True)


@router.delete("/{countdown_id}/follow", response_model=CountdownResponse)
async def unfollow_countdown(
    countdown_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CountdownService = Depends(get_countdown_service),
) -> CountdownResponse:
    """@brief Unfollow a countdown."""
    return await svc.follow(user, countdown_id, False)
