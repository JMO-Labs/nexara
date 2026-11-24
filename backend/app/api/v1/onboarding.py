"""
@file onboarding.py
@brief Onboarding wizard routes and the admin required-steps setting.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_role
from app.core.deps_onboarding import get_onboarding_service
from app.models.user import User
from app.schemas.onboarding import OnboardingState, RequiredUpdate, StepUpdate
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
admin_router = APIRouter(
    prefix="/admin", tags=["admin-onboarding"], dependencies=[Depends(require_role("admin"))]
)


@router.get("", response_model=OnboardingState)
async def get_state(svc: OnboardingService = Depends(get_onboarding_service)) -> OnboardingState:
    """@brief Wizard state: step, done, required steps and sign-up/SSO prefill."""
    return await svc.state()


@router.put("", response_model=OnboardingState)
async def put_step(
    body: StepUpdate, svc: OnboardingService = Depends(get_onboarding_service)
) -> OnboardingState:
    """@brief Save the wizard position so the member can resume."""
    return await svc.set_step(body.step)


@router.post("/complete", response_model=OnboardingState)
async def complete(svc: OnboardingService = Depends(get_onboarding_service)) -> OnboardingState:
    """@brief Finish onboarding; 400 ``onboarding_incomplete`` lists missing required steps."""
    return await svc.complete()


@admin_router.get("/onboarding", response_model=RequiredUpdate)
async def admin_get(
    svc: OnboardingService = Depends(get_onboarding_service),
) -> RequiredUpdate:
    """@brief Admin: steps currently marked required."""
    return RequiredUpdate(required=await svc.configured())


@admin_router.put("/onboarding", response_model=RequiredUpdate)
async def admin_put(
    body: RequiredUpdate,
    user: User = Depends(get_current_user),
    svc: OnboardingService = Depends(get_onboarding_service),
) -> RequiredUpdate:
    """@brief Admin: choose which steps new members cannot skip."""
    return RequiredUpdate(required=await svc.set_required(user.id, list(body.required)))
