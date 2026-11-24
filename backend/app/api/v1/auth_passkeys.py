"""
@file auth_passkeys.py
@brief /auth/passkeys/*: WebAuthn registration, login and management.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user
from app.core.deps_two_factor import get_passkey_service
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.schemas.common import MessageResponse
from app.schemas.passkey import (
    LoginOptionsBody,
    LoginVerifyBody,
    PasskeyName,
    PasskeyOut,
    RegisterVerifyBody,
)
from app.services.auth.passkeys import PasskeyService

router = APIRouter(prefix="/passkeys")


@router.post("/register/options")
async def register_options(
    user: User = Depends(get_current_user),
    svc: PasskeyService = Depends(get_passkey_service),
) -> dict[str, Any]:
    """@brief WebAuthn creation options for the signed-in user."""
    return await svc.register_options(user)


@router.post("/register/verify", response_model=PasskeyOut)
async def register_verify(
    body: RegisterVerifyBody,
    user: User = Depends(get_current_user),
    svc: PasskeyService = Depends(get_passkey_service),
) -> Any:
    """@brief Verify the attestation and store the passkey."""
    return await svc.register_verify(user, body.credential, body.name)


@router.post("/login/options")
@limiter.limit("10/minute")
async def login_options(
    request: Request,
    body: LoginOptionsBody,
    svc: PasskeyService = Depends(get_passkey_service),
) -> dict[str, Any]:
    """@brief WebAuthn request options (discoverable when no email)."""
    return await svc.login_options(body.email)


@router.post("/login/verify", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login_verify(
    request: Request,
    body: LoginVerifyBody,
    response: Response,
    svc: PasskeyService = Depends(get_passkey_service),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Passwordless sign-in, or the 2FA step when ``pending_token`` is given."""
    from app.api.v1.auth import _set_refresh_cookie

    result = await svc.login_verify(body.credential, body.pending_token, request)
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(access_token=result["access_token"], expires_in=result["expires_in"])


@router.get("", response_model=list[PasskeyOut])
async def list_passkeys(
    user: User = Depends(get_current_user),
    svc: PasskeyService = Depends(get_passkey_service),
) -> Any:
    """@brief The signed-in user's passkeys."""
    return await svc.list_passkeys(user)


@router.patch("/{passkey_id}", response_model=PasskeyOut)
async def rename_passkey(
    passkey_id: uuid.UUID,
    body: PasskeyName,
    user: User = Depends(get_current_user),
    svc: PasskeyService = Depends(get_passkey_service),
) -> Any:
    """@brief Rename a passkey."""
    return await svc.rename(user, passkey_id, body.name)


@router.delete("/{passkey_id}", response_model=MessageResponse)
async def delete_passkey(
    passkey_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: PasskeyService = Depends(get_passkey_service),
) -> MessageResponse:
    """@brief Remove a passkey."""
    await svc.remove(user, passkey_id)
    return MessageResponse(message="Passkey removed")
