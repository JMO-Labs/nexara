"""
@file daily_questions.py
@brief Daily-question bank API: member suggestions and admin moderation.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.repositories.question_bank_repo import QuestionBankRepository
from app.schemas.prompt import QuestionOut, QuestionText
from app.services.daily_question_service import DailyQuestionService

router = APIRouter(tags=["daily-questions"])


def _service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> DailyQuestionService:
    """@brief Build DailyQuestionService for the configured community."""
    return DailyQuestionService(QuestionBankRepository(db), uuid.UUID(settings.COMMUNITY_ID), db)


@router.post("/daily-questions/suggest", response_model=QuestionOut, status_code=201)
async def suggest_question(
    body: QuestionText,
    user: User = Depends(get_current_user),
    service: DailyQuestionService = Depends(_service),
) -> QuestionOut:
    """@brief Suggest a question (pending approval); 3 per day per user."""
    return QuestionOut.model_validate(await service.suggest(user.id, body.text))


@router.get("/admin/daily-questions", response_model=list[QuestionOut])
async def list_questions(
    status: Literal["approved", "pending", "rejected"] = Query("pending"),
    user: User = Depends(require_role("admin")),
    service: DailyQuestionService = Depends(_service),
) -> list[QuestionOut]:
    """@brief List bank questions by status (admin)."""
    return [QuestionOut.model_validate(r) for r in await service.list_by_status(status)]


@router.post("/admin/daily-questions", response_model=QuestionOut, status_code=201)
async def add_question(
    body: QuestionText,
    user: User = Depends(require_role("admin")),
    service: DailyQuestionService = Depends(_service),
) -> QuestionOut:
    """@brief Add an approved question (admin)."""
    return QuestionOut.model_validate(await service.add(body.text))


@router.post("/admin/daily-questions/{question_id}/approve", response_model=QuestionOut)
async def approve_question(
    question_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: DailyQuestionService = Depends(_service),
) -> QuestionOut:
    """@brief Approve a pending question (admin)."""
    return QuestionOut.model_validate(await service.moderate(question_id, "approved"))


@router.post("/admin/daily-questions/{question_id}/reject", response_model=QuestionOut)
async def reject_question(
    question_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: DailyQuestionService = Depends(_service),
) -> QuestionOut:
    """@brief Reject a pending question (admin)."""
    return QuestionOut.model_validate(await service.moderate(question_id, "rejected"))
