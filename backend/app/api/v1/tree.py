"""
@file tree.py
@brief Family tree and group relationship tree endpoints.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.repositories.tree_repo import TreeRepository
from app.schemas.tree import TreeOut
from app.services.tree_service import TreeService

router = APIRouter(prefix="/tree", tags=["tree"])


def _service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TreeService:
    """@brief TreeService bound to the request session."""
    return TreeService(
        RelationRepository(db),
        TreeRepository(db),
        ProfileRepository(db),
        CommunityRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
    )


@router.get("/family", response_model=TreeOut)
async def family_tree(
    root: uuid.UUID | None = None,
    gens: int = Query(3, ge=1, le=10),
    user: User = Depends(get_current_user),
    svc: TreeService = Depends(_service),
) -> Any:
    """@brief Relatives around ``root`` (default you); hidden ones are masked."""
    return await svc.family(user, root, gens)


@router.get("/group/{slug}", response_model=TreeOut)
async def group_tree(
    slug: str,
    user: User = Depends(get_current_user),
    svc: TreeService = Depends(_service),
) -> Any:
    """@brief Relations among the members of a group you belong to."""
    return await svc.group(user, slug)
