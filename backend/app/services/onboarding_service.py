"""
@file onboarding_service.py
@brief Onboarding wizard state, completion rules and the admin required-steps setting.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.features import is_enabled
from app.core.i18n import _
from app.models.user import User
from app.repositories.onboarding_repo import OnboardingRepository
from app.repositories.two_factor_repo import TwoFactorRepository
from app.schemas.onboarding import ADMIN_REQUIRABLE, STEPS, OnboardingState, Prefill
from app.services.auth.policy import GRACE, covers, factor_methods


def _relations_on(community: Any) -> bool:
    """@brief Relations feature on (a missing row fails open, like ``feature_on``)."""
    return community is None or is_enabled(community, "relations")


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
        *,
        two_factor_repo: TwoFactorRepository,
    ) -> None:
        self._repo, self._cid, self._session = repo, community_id, session
        self._user, self._audit, self._ip = user, audit, ip
        self._two_factor = two_factor_repo

    async def _covered(self) -> bool:
        """@brief Whether the community 2FA policy covers this member."""
        return covers(await self._two_factor.get_policy(self._cid), self._user)

    async def _required(self) -> list[str]:
        """
        @brief Admin-required steps plus ``security`` when the 2FA policy covers the user.
               ``family`` is dropped while the relations feature is off.
        """
        community = await self._repo.get_community(self._cid)
        chosen = community.onboarding_required if community else []
        required = [s for s in STEPS if s in chosen]
        if "family" in required and not _relations_on(community):
            required.remove("family")
        if await self._covered() and "security" not in required:
            required.append("security")
        return required

    async def _security_now(self) -> bool:
        """@brief Past the 2FA grace period without a factor: only the security step works."""
        since = self._user.two_factor_required_since
        if since is None or datetime.now(UTC) < since + GRACE or not await self._covered():
            return False
        return not await factor_methods(self._session, self._user)

    async def state(self) -> OnboardingState:
        """@brief Current step, done flag, required steps and SSO/sign-up prefill."""
        u = self._user
        return OnboardingState(
            step=u.onboarding_step,
            done=u.onboarding_done_at is not None,
            required=await self._required(),
            security_now=await self._security_now(),
            prefill=Prefill(display_name=u.display_name, avatar_url=u.avatar_url, email=u.email),
        )

    async def configured(self) -> list[str]:
        """@brief The admin-chosen required steps (without the automatic security step)."""
        community = await self._repo.get_community(self._cid)
        return [s for s in STEPS if s in (community.onboarding_required if community else [])]

    async def set_step(self, step: int) -> OnboardingState:
        """
        @brief Persist the wizard position (resume point).
        @throws AppError 400 ``onboarding_step_incomplete`` when advancing past an
                unfinished required step. A finished member revisiting the
                wizard (``?resume=1``) changes nothing.
        """
        if self._user.onboarding_done_at is not None:
            return await self.state()
        missing = [s for s in await self._missing(await self._required()) if STEPS.index(s) < step]
        if missing:
            raise AppError(
                code="onboarding_step_incomplete",
                message=_("Finish this required step first"),
                status_code=400,
                details={"missing": missing},
            )
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
        if "family" in required and not await self._repo.has_family(self._cid, u.id):
            missing.append("family")
        if "security" in required and not await factor_methods(self._session, u):
            missing.append("security")
        return [s for s in STEPS if s in missing]

    async def complete(self) -> OnboardingState:
        """
        @brief Finish onboarding.
        @throws AppError 400 ``onboarding_incomplete`` listing missing required steps.
        """
        if self._user.onboarding_done_at is not None:
            return await self.state()  # already finished: completing again is a no-op
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
        """
        @brief Admin: choose the steps new members cannot skip (audited).
        @throws AppError 422 ``relations_disabled`` when requiring ``family`` with relations off.
        """
        clean = [s for s in ADMIN_REQUIRABLE if s in required]
        community = await self._repo.get_community(self._cid)
        if community is None:
            raise NotFoundError(_("Community not found"))
        if "family" in clean and not _relations_on(community):
            raise AppError(
                code="relations_disabled",
                message=_("Turn on relations before requiring the family step"),
                status_code=422,
            )
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
