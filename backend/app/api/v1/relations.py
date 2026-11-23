"""
@file relations.py
@brief Relation endpoints: request, confirm, remove, list.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.relation import RelationCreate, RelationOut
from app.services.notification_service import NotificationService
from app.services.relation_service import RelationService

router = APIRouter(prefix="/relations", tags=["relations"])


def build_relation_service(db: AsyncSession, cid: uuid.UUID) -> RelationService:
    """@brief RelationService wired to ``db`` (also used by the memorials route)."""
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return RelationService(
        RelationRepository(db),
        ProfileRepository(db),
        HouseholdRepository(db),
        CommunityRepository(db),
        notif,
        cid,
    )


def _service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> RelationService:
    """@brief RelationService bound to the request session."""
    return build_relation_service(db, uuid.UUID(settings.COMMUNITY_ID))


@router.post("", status_code=201, response_model=RelationOut)
async def request_relation(
    body: RelationCreate,
    user: User = Depends(get_current_user),
    svc: RelationService = Depends(_service),
) -> Any:
    """@brief Ask to link a member (pending) or your own household member (confirmed)."""
    rel = await svc.request(
        user,
        to_user_id=body.to_user_id,
        to_member_id=body.to_member_id,
        kind=body.kind,
        label=body.label,
    )
    out = await svc.list_for(user.id, user)
    return next(r for r in out if r.id == rel.id)


@router.get("", response_model=list[RelationOut])
async def list_relations(
    user_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    svc: RelationService = Depends(_service),
) -> Any:
    """@brief Relations of ``user_id`` (default: you) that you may see."""
    return await svc.list_for(user_id or user.id, user)


@router.get("/requests", response_model=list[RelationOut])
async def list_requests(
    user: User = Depends(get_current_user), svc: RelationService = Depends(_service)
) -> Any:
    """@brief Pending requests sent to you."""
    return await svc.requests(user)


@router.post("/{relation_id}/confirm", response_model=dict)
async def confirm_relation(
    relation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: RelationService = Depends(_service),
) -> Any:
    """@brief Accept a request sent to you."""
    await svc.confirm(relation_id, user)
    return {"message": "Confirmed"}


@router.delete("/{relation_id}", status_code=204)
async def remove_relation(
    relation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: RelationService = Depends(_service),
) -> Response:
    """@brief Decline, cancel or remove a relation (either side or an admin)."""
    await svc.remove(relation_id, user)
    return Response(status_code=204)
