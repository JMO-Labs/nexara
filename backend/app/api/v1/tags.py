"""
@file tags.py
@brief Tag endpoints: list tags on a post/comment/photo, tag people in a
       photo, remove a tag, and a person's Tagged feed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.common import MessageResponse
from app.schemas.tag import TagCreate, TaggedPage, TagResponse
from app.services.notification_service import NotificationService
from app.services.tag_service import TagService

router = APIRouter(tags=["tags"])


def _service(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagService:
    """@brief TagService bound to the request session."""
    notifications = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=user.community_id,
        dispatcher=get_dispatcher(),
    )
    return TagService(TagRepository(db), PostRepository(db), notifications, user.community_id)


@router.get("/tags/{target_type}/{target_id}", response_model=list[TagResponse])
async def list_tags(
    target_type: Literal["post", "comment", "media"],
    target_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: TagService = Depends(_service),
) -> Any:
    """@brief People tagged on something the viewer can see."""
    return await svc.list_for(target_type, target_id, user)


@router.post("/media/{media_id}/tags", response_model=list[TagResponse], status_code=201)
async def tag_photo(
    media_id: uuid.UUID,
    body: TagCreate,
    user: User = Depends(get_current_user),
    svc: TagService = Depends(_service),
) -> Any:
    """@brief Tag a member or household member/pet in a photo; returns the photo's tags."""
    if body.household_id is not None:
        return await svc.tag_household(media_id, body.household_id, user)
    return await svc.tag_media(media_id, body.user_id, user)  # type: ignore[arg-type]


@router.delete("/tags/{tag_id}", response_model=MessageResponse)
async def remove_tag(
    tag_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: TagService = Depends(_service),
) -> MessageResponse:
    """@brief Remove a tag (tagged person, tagger, photo owner or admin)."""
    await svc.remove(tag_id, user)
    return MessageResponse(message="Tag removed")


@router.get("/users/{user_id}/tagged", response_model=TaggedPage)
async def tagged_feed(
    user_id: uuid.UUID,
    kind: Literal["posts", "photos"] = Query("posts"),
    before: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    svc: TagService = Depends(_service),
) -> Any:
    """@brief Posts or photos this person is tagged in that the viewer can see."""
    return await svc.tagged(user_id, user, kind, before)


@router.get("/household/{member_id}/tagged", response_model=TaggedPage)
async def household_tagged(
    member_id: uuid.UUID,
    before: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    svc: TagService = Depends(_service),
) -> Any:
    """@brief Photos a household member/pet is tagged in that the viewer can see."""
    return await svc.household_photos(member_id, user, before)
