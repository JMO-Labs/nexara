"""
@file auth.py
@brief Pydantic schemas for authentication request/response payloads.

Covers local login, registration, token refresh, 2FA enrollment/verification,
OIDC callback, password reset, and invite management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field


# ---------------------------------------------------------------------------
# Permissive email validator for self-hosted environments.
#
# Pydantic's EmailStr rejects non-standard TLDs (.local, .lan, .home,
# .internal) that are common in homelab / self-hosted setups.  This
# validator accepts any domain with at least one character after '@'.
# ---------------------------------------------------------------------------
def _validate_selfhost_email(value: str) -> str:
    v = value.strip()
    if not v or "@" not in v:
        raise ValueError("A valid email address is required (must contain '@').")
    local, _, domain = v.partition("@")
    if not local:
        raise ValueError("Email address is missing the part before '@'.")
    if not domain:
        raise ValueError("Email address is missing the domain after '@'.")
    if domain.startswith(".") or domain.endswith("."):
        raise ValueError("The domain part of the email address is not valid.")
    if ".." in domain:
        raise ValueError("The domain part of the email address is not valid.")
    return v.lower()


SelfHostEmail = Annotated[str, AfterValidator(_validate_selfhost_email)]


class LoginRequest(BaseModel):
    """@brief Credentials for local email/password login."""

    email: SelfHostEmail
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """@brief Payload for new user registration."""

    email: SelfHostEmail
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=12)
    display_name: str = Field(..., min_length=1, max_length=100)
    invite_token: str | None = None


class TokenResponse(BaseModel):
    """@brief Successful authentication response with access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class LoginResponse(BaseModel):
    """
    @brief Login result that may require 2FA completion.

    When ``requires_2fa`` is True, the client must POST the TOTP code
    along with the ``two_factor_token`` to ``/auth/2fa/verify``.
    """

    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    requires_2fa: bool = False
    two_factor_token: str | None = None


class RefreshResponse(BaseModel):
    """@brief New access token issued after refresh-token rotation."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TwoFactorEnrollResponse(BaseModel):
    """@brief Data returned when a user starts 2FA enrollment."""

    secret: str = Field(description="Base32 TOTP secret for manual entry")
    otpauth_uri: str = Field(description="otpauth:// URI for QR code generation")


class TwoFactorVerifyRequest(BaseModel):
    """@brief Payload to verify a TOTP code (enrollment or login)."""

    code: str = Field(..., min_length=6, max_length=8, description="TOTP or backup code")


class TwoFactorLoginRequest(BaseModel):
    """@brief Payload to complete a 2FA-pending login."""

    two_factor_token: str
    code: str = Field(..., min_length=6, max_length=8)


class TwoFactorVerifyResponse(BaseModel):
    """@brief Response after successful 2FA enrollment verification."""

    backup_codes: list[str] = Field(description="One-time recovery codes")


class MagicLinkRequestPayload(BaseModel):
    """@brief Request a magic link for passwordless login."""

    email: SelfHostEmail


class PasswordResetRequestPayload(BaseModel):
    """@brief Request a password reset email."""

    email: SelfHostEmail


class PasswordResetConfirmPayload(BaseModel):
    """@brief Apply a new password with a valid reset token."""

    token: str
    new_password: str = Field(..., min_length=12)


class OIDCCallbackParams(BaseModel):
    """@brief Query parameters returned by the OIDC provider."""

    code: str
    state: str


class OAuthProviderListItem(BaseModel):
    """
    @brief Minimal provider info for login page buttons.

    slug, display_name, icon_url only.
    """

    slug: str
    display_name: str
    icon_url: str | None = None


class AuthConfigResponse(BaseModel):
    """
    @brief Public auth configuration exposed to the frontend.

    oidc_enabled is kept for backward compat (True if any OAuth providers).
    """

    oidc_enabled: bool
    registration_enabled: bool
    local_auth_enabled: bool = True
    oauth_providers: list[OAuthProviderListItem] = []


class LogoutResponse(BaseModel):
    """
    @brief Logout response with optional IdP end-session URL.

    When the user has an OAuth link to a provider with end_session_endpoint,
    the frontend should redirect to end_session_url for RP-initiated logout.
    """

    message: str
    end_session_url: str | None = None


class InviteCreateRequest(BaseModel):
    """@brief Admin request to create an invite."""

    email: SelfHostEmail
    role: str = Field(default="member", pattern=r"^(admin|member|viewer)$")


class InviteResponse(BaseModel):
    """@brief Public representation of an invite."""

    id: UUID
    email: str
    role: str
    created_by: UUID
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
