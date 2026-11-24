"""
@file onboarding_service.py
@brief Onboarding wizard state, completion rules and the admin required-steps setting.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.onboarding_repo import OnboardingRepository
from app.repositories.two_factor_repo import TwoFactorRepository
from app.schemas.onboarding import STEPS, OnboardingState, Prefill
from app.services.auth.policy import covers, factor_methods


class OnboardingService:
    """@brief Per-member onboarding progress for one community."""

    def __init__(
        self,
        repo: OnboardingRepository,
        community_id: uuid.UUID,
        session: AsyncSession,
        user: User,
        audit: Any = None,
        ip: str | None = None,
    ) -> None:
        self._repo, self._cid, self._session = repo, community_id, session
        self._user, self._audit, self._ip = user, audit, ip

    async def _required(self) -> list[str]:
        """@brief Admin-required steps plus ``security`` when the 2FA policy covers the user."""
        community = await self._repo.get_community(self._cid)
        required = [s for s in STEPS if s in (community.onboarding_required if community else [])]
        policy = await TwoFactorRepository(self._session).get_policy(self._cid)
        if covers(policy, self._user) and "security" not in required:
            required.append("security")
        return required

    async def state(self) -> OnboardingState:
        """@brief Current step, done flag, required steps and SSO/sign-up prefill."""
        u = self._user
        return OnboardingState(
            step=u.onboarding_step,
            done=u.onboarding_done_at is not None,
            required=await self._required(),
            prefill=Prefill(display_name=u.display_name, avatar_url=u.avatar_url, email=u.email),
        )

    async def configured(self) -> list[str]:
        """@brief The admin-chosen required steps (without the automatic security step)."""
        community = await self._repo.get_community(self._cid)
        return [s for s in STEPS if s in (community.onboarding_required if community else [])]

    async def set_step(self, step: int) -> OnboardingState:
        """@brief Persist the wizard position (resume point)."""
        await self._repo.set_step(self._user, step)
        return await self.state()

    async def _missing(self, required: list[str]) -> list[str]:
        """@brief Required steps whose data is still absent."""
        u = self._user
        checks = {
            "profile": bool(u.avatar_url),
            "birthday": u.birthday is not None,
            "contact": bool(u.phone or u.contact_email or u.address or u.location),
        }
        missing = [s for s in required if s in checks and not checks[s]]
        if "family" in required and not await self._repo.has_relation(self._cid, u.id):
            missing.append("family")
        if "security" in required and not await factor_methods(self._session, u):
            missing.append("security")
        return [s for s in STEPS if s in missing]

    async def complete(self) -> OnboardingState:
        """
        @brief Finish onboarding.
        @throws AppError 400 ``onboarding_incomplete`` listing missing required steps.
        """
        missing = await self._missing(await self._required())
        if missing:
            raise AppError(
                code="onboarding_incomplete",
                message=_("Finish the required steps first"),
                status_code=400,
                details={"missing": missing},
            )
        await self._repo.set_step(self._user, len(STEPS))
        await self._repo.mark_done(self._user)
        return await self.state()

    async def set_required(self, actor_id: uuid.UUID, required: list[str]) -> list[str]:
        """@brief Admin: choose the steps new members cannot skip (audited)."""
        from app.schemas.onboarding import ADMIN_REQUIRABLE

        clean = [s for s in ADMIN_REQUIRABLE if s in required]
        if await self._repo.get_community(self._cid) is None:
            raise NotFoundError(_("Community not found"))
        await self._repo.set_required(self._cid, clean)
        if self._audit is not None:
            await self._audit.append(
                actor_id=actor_id,
                action="onboarding.required_updated",
                target_type="community",
                target_id=self._cid,
                extra_data={"required": clean},
                ip_address=self._ip,
            )
        return clean
