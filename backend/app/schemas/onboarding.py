"""
@file onboarding.py
@brief Schemas for the onboarding wizard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

StepId = Literal["profile", "birthday", "contact", "family", "notify", "security"]
STEPS: tuple[str, ...] = ("profile", "birthday", "contact", "family", "notify", "security")
"""@brief Wizard steps in order."""
ADMIN_REQUIRABLE: tuple[str, ...] = ("profile", "birthday", "contact", "family")
"""@brief Steps an admin may mark required (notify is a preference; security follows policy)."""


class Prefill(BaseModel):
    """@brief Values already known from sign-up / SSO."""

    display_name: str
    avatar_url: str | None = None
    email: str


class OnboardingState(BaseModel):
    """@brief Wizard state for the signed-in member."""

    step: int
    done: bool
    required: list[str]
    security_now: bool = False  # past 2FA grace without a factor: open on security
    steps: list[str] = list(STEPS)
    prefill: Prefill


class StepUpdate(BaseModel):
    """@brief Save the wizard position."""

    step: int = Field(ge=0, le=len(STEPS))


class RequiredUpdate(BaseModel):
    """@brief Admin: steps that cannot be skipped."""

    required: list[StepId]
