"""
@file passkeys.py
@brief WebAuthn passkeys: registration, passwordless / second-factor login, management.

Challenges live in Valkey keyed by the challenge itself (single use via GETDEL,
5 min TTL). Only public keys are stored.
"""

from __future__ import annotations

import json
import uuid
from functools import partial
from typing import TYPE_CHECKING, Any

import structlog
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import Settings
from app.core.exceptions import AppError, AuthenticationError, NotFoundError
from app.core.i18n import _
from app.core.security import decode_token
from app.core.valkey import DB_CACHE, get_pool
from app.models.passkey import Passkey
from app.models.user import User
from app.repositories.passkey_repo import PasskeyRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.services.auth.memorial_guard import reject_memorialized
from app.services.auth.pending_link import create_link
from app.services.auth.signin_log import log_failure, log_success
from app.services.auth.sso_only import assert_password_auth_allowed
from app.services.auth.token_utils import issue_tokens
from app.services.auth.totp_replay import clear_user_attempts, reserve_attempt

if TYPE_CHECKING:
    from fastapi import Request

logger = structlog.get_logger(__name__)

CHALLENGE_TTL = 300
_KEY = "webauthn:chal:"


def _bad(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=400)


class PasskeyService:
    """@brief Passkey operations for one community."""

    def __init__(
        self,
        repo: PasskeyRepository,
        users: UserRepository,
        tokens: TokenRepository,
        audit: Any,
        settings: Settings,
        community_id: uuid.UUID,
        ip: str | None = None,
    ) -> None:
        self._repo, self._users, self._tokens, self._audit = repo, users, tokens, audit
        self._s, self._cid, self._ip = settings, community_id, ip

    # -- challenge store ---------------------------------------------------

    async def _put(self, challenge: bytes, kind: str, user_id: uuid.UUID | None) -> None:
        val = json.dumps({"kind": kind, "user": str(user_id) if user_id else None})
        try:
            await get_pool(self._s, DB_CACHE).set(
                _KEY + bytes_to_base64url(challenge), val, ex=CHALLENGE_TTL
            )
        except RedisError as exc:
            raise AppError(
                code="service_unavailable", message=_("Try again shortly"), status_code=503
            ) from exc

    async def _take(self, credential: dict[str, Any], kind: str) -> tuple[bytes, str | None]:
        """@brief Pop the challenge the browser signed (single use)."""
        try:
            cdj = base64url_to_bytes(credential["response"]["clientDataJSON"])
            chal = str(json.loads(cdj)["challenge"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _bad("invalid_passkey", _("Invalid passkey response")) from exc
        try:
            raw = await get_pool(self._s, DB_CACHE).getdel(_KEY + chal)
        except RedisError as exc:
            raise AppError(
                code="service_unavailable", message=_("Try again shortly"), status_code=503
            ) from exc
        data = json.loads(raw) if raw else None
        if not data or data["kind"] != kind:
            raise _bad("challenge_expired", _("Passkey challenge expired or already used"))
        return base64url_to_bytes(chal), data["user"]

    # -- registration ------------------------------------------------------

    async def register_options(self, user: User) -> dict[str, Any]:
        """@brief WebAuthn creation options excluding the user's existing passkeys."""
        existing = await self._repo.list_for_user(user.id)
        opts = generate_registration_options(
            rp_id=self._s.webauthn_rp_id,
            rp_name=self._s.APP_NAME,
            user_id=user.id.bytes,
            user_name=user.email,
            user_display_name=getattr(user, "display_name", None) or user.email,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=p.credential_id) for p in existing
            ],
        )
        await self._put(opts.challenge, "register", user.id)
        return dict(json.loads(options_to_json(opts)))

    async def register_verify(self, user: User, credential: dict[str, Any], name: str) -> Passkey:
        """@brief Verify the attestation and store the new passkey."""
        challenge, owner = await self._take(credential, "register")
        if owner != str(user.id):
            raise _bad("challenge_expired", _("Passkey challenge expired or already used"))
        try:
            v = verify_registration_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self._s.webauthn_rp_id,
                expected_origin=self._s.webauthn_origins,
            )
        except (WebAuthnException, ValueError, KeyError) as exc:
            logger.info("passkey.register_rejected", reason=str(exc))
            raise _bad("invalid_passkey", _("Passkey could not be verified")) from exc
        if await self._repo.get_by_credential(v.credential_id):
            raise AppError(
                code="passkey_exists", message=_("Passkey already registered"), status_code=409
            )
        transports = credential.get("response", {}).get("transports") or []
        try:
            pk = await self._repo.add(
                Passkey(
                    user_id=user.id,
                    credential_id=v.credential_id,
                    public_key=v.credential_public_key,
                    sign_count=v.sign_count,
                    transports=[str(t) for t in transports],
                    name=name.strip()[:100] or "Passkey",
                )
            )
        except IntegrityError as exc:
            raise AppError(
                code="passkey_exists", message=_("Passkey already registered"), status_code=409
            ) from exc
        await self._log(user.id, "passkey.added", pk.id)
        return pk

    # -- login -------------------------------------------------------------

    async def login_options(
        self, email: str | None, pending_token: str | None = None
    ) -> dict[str, Any]:
        """
        @brief Assertion options; empty allowCredentials = discoverable login.

        A valid ``pending_token`` (first factor done) lists that user's passkeys so
        non-discoverable security keys work for the 2FA step.
        """
        allow: list[PublicKeyCredentialDescriptor] = []
        user = await self._pending_user(pending_token) if pending_token else None
        if user is None and email:
            user = await self._users.find_by_email(email)
        if user and user.community_id == self._cid:
            allow = [
                PublicKeyCredentialDescriptor(id=p.credential_id)
                for p in await self._repo.list_for_user(user.id)
            ]
        opts = generate_authentication_options(
            rp_id=self._s.webauthn_rp_id,
            allow_credentials=allow,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        await self._put(opts.challenge, "login", None)
        return dict(json.loads(options_to_json(opts)))

    async def _pending_user(self, token: str) -> User | None:
        """@brief Owner of a valid ``2fa_pending`` token, else None."""
        try:
            payload = decode_token(token, expected_type="2fa_pending", settings=self._s)
            return await self._users.get_by_id(uuid.UUID(payload["sub"]), self._cid)
        except (ValueError, KeyError):
            return None

    async def login_verify(
        self, credential: dict[str, Any], pending_token: str | None, request: Request | None
    ) -> dict[str, Any]:
        """
        @brief Verify an assertion and issue tokens.

        With ``pending_token`` the passkey completes that user's 2FA step;
        without it the passkey must have verified the user (UV) on its own.
        @raises AppError 400 on any verification failure, ``passkey_cloned`` on counter regress.
        """
        fail = partial(log_failure, self._s, request=request)
        pending_user: uuid.UUID | None = None
        held_link: dict[str, Any] | None = None
        if pending_token:
            try:
                payload = decode_token(pending_token, expected_type="2fa_pending", settings=self._s)
            except ValueError as exc:
                await fail(None, None, "passkey", "bad_2fa_session")
                raise AuthenticationError(message=str(exc)) from exc
            pending_user = uuid.UUID(payload["sub"])
            held_link = payload.get("oauth_link")
            if not await reserve_attempt(pending_token, pending_user, self._s):
                await fail(None, None, "passkey", "bad_2fa_session")
                raise AuthenticationError(message=_("Invalid 2FA session"))
        else:
            try:
                await assert_password_auth_allowed(self._repo.session, self._cid)
            except AppError:
                await fail(None, None, "passkey", "sso_only")
                raise
        try:
            challenge, _owner = await self._take(credential, "login")
            raw_id = base64url_to_bytes(str(credential.get("rawId") or credential.get("id")))
        except (AppError, ValueError):
            await fail(None, None, "passkey", "bad_challenge")
            raise
        pk = await self._repo.get_by_credential(raw_id)
        user = await self._users.get_by_id(pk.user_id, self._cid) if pk else None
        if pk is None or user is None or (pending_user and pending_user != user.id):
            await fail(user, None, "passkey", "unknown_credential")
            raise _bad("invalid_passkey", _("Passkey could not be verified"))
        try:
            reject_memorialized(user)
        except AppError:
            await fail(user, user.email, "passkey", "memorialized")
            raise
        if not user.is_active:
            await fail(user, user.email, "passkey", "inactive")
            raise _bad("invalid_passkey", _("Passkey could not be verified"))
        handle = credential.get("response", {}).get("userHandle")
        try:
            if handle and base64url_to_bytes(str(handle)) != user.id.bytes:
                raise ValueError("userHandle mismatch")
            v = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self._s.webauthn_rp_id,
                expected_origin=self._s.webauthn_origins,
                credential_public_key=pk.public_key,
                # Counter policy is ours (below) so regressions get the passkey_cloned code.
                credential_current_sign_count=0,
                require_user_verification=pending_user is None,
            )
        except (WebAuthnException, ValueError, KeyError) as exc:
            logger.info("passkey.login_rejected", reason=str(exc))
            await fail(user, user.email, "passkey", "bad_assertion")
            raise _bad("invalid_passkey", _("Passkey could not be verified")) from exc
        if pending_user is None and user.password_hash is None:
            await fail(user, user.email, "passkey", "sso_user")
            raise AppError(
                code="sso_login_required",
                message=_("Sign in with single sign-on"),
                status_code=403,
            )
        if not await self._repo.touch(pk, v.new_sign_count):
            await fail(user, user.email, "passkey", "cloned")
            raise _bad("passkey_cloned", _("Passkey rejected: possible cloned authenticator"))
        if pending_token and pending_user:
            await clear_user_attempts(pending_user, self._s)
            await create_link(self._repo.session, pending_user, held_link)
        await self._users.update_last_seen(user.id)
        await log_success(self._repo.session, self._s, user, "passkey", request)
        return await issue_tokens(self._tokens, user, self._s)

    # -- management --------------------------------------------------------

    async def list_passkeys(self, user: User) -> list[Passkey]:
        """@brief The user's passkeys."""
        return await self._repo.list_for_user(user.id)

    async def rename(self, user: User, passkey_id: uuid.UUID, name: str) -> Passkey:
        """@brief Rename an owned passkey."""
        return await self._repo.rename(await self._owned(user, passkey_id), name.strip())

    async def remove(self, user: User, passkey_id: uuid.UUID) -> None:
        """@brief Delete an owned passkey (audited)."""
        pk = await self._owned(user, passkey_id)
        await self._repo.delete(pk)
        await self._log(user.id, "passkey.removed", passkey_id)

    async def _owned(self, user: User, passkey_id: uuid.UUID) -> Passkey:
        pk = await self._repo.get_owned(passkey_id, user.id)
        if pk is None:
            raise NotFoundError(_("Passkey not found"))
        return pk

    async def _log(self, actor: uuid.UUID, action: str, target: uuid.UUID) -> None:
        await self._audit.append(
            actor_id=actor,
            action=action,
            target_type="passkey",
            target_id=target,
            ip_address=self._ip,
        )
