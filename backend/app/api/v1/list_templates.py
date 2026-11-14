"""
@file list_templates.py
@brief List templates API: CRUD and clone-to-list.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response

from app.core.dependencies import get_current_user
from app.core.list_dependencies import get_community_id, get_list_template_service
from app.models.user import User
from app.schemas.list import ListOut
from app.schemas.list_template import (
    ListTemplateClone,
    ListTemplateCreate,
    ListTemplateOut,
    ListTemplatePage,
    ListTemplateUpdate,
)
from app.services.list_template_service import ListTemplateService

router = APIRouter(prefix="/list_templates", tags=["list_templates"])


@router.get("", response_model=ListTemplatePage)
async def list_templates(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> ListTemplatePage:
    """@brief Keyset page of templates visible to the caller."""
    rows, nxt = await service.list_for_community(community_id, user.id, cursor, limit)
    return ListTemplatePage(
        templates=[ListTemplateOut.model_validate(r) for r in rows],
        cursor=nxt,
        has_more=nxt is not None,
    )


@router.post("", response_model=ListTemplateOut, status_code=201)
async def create_template(
    body: ListTemplateCreate,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> ListTemplateOut:
    """@brief Create a template."""
    tpl = await service.create(community_id, user.id, body.model_dump())
    return ListTemplateOut.model_validate(tpl)


@router.get("/{template_id}", response_model=ListTemplateOut)
async def get_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> ListTemplateOut:
    """@brief Fetch a visible template (404 otherwise)."""
    tpl = await service.get_by_id(community_id, template_id, user.id)
    return ListTemplateOut.model_validate(tpl)


@router.put("/{template_id}", response_model=ListTemplateOut)
async def update_template(
    template_id: uuid.UUID,
    body: ListTemplateUpdate,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> ListTemplateOut:
    """@brief Update a template (author only; 403 otherwise)."""
    data = body.model_dump(exclude_unset=True)
    tpl = await service.update(community_id, template_id, user.id, data)
    return ListTemplateOut.model_validate(tpl)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> Response:
    """@brief Soft-delete a template (author only)."""
    await service.delete(community_id, template_id, user.id)
    return Response(status_code=204)


@router.post("/{template_id}/clone", response_model=ListOut, status_code=201)
async def clone_template(
    template_id: uuid.UUID,
    body: ListTemplateClone,
    user: User = Depends(get_current_user),
    community_id: uuid.UUID = Depends(get_community_id),
    service: ListTemplateService = Depends(get_list_template_service),
) -> ListOut:
    """@brief Instantiate a template as a new list."""
    new = await service.clone_template_to_list(
        community_id,
        template_id,
        user.id,
        title=body.title,
        visibility=body.visibility,
        include_items=body.include_items,
    )
    return ListOut.model_validate(new)
