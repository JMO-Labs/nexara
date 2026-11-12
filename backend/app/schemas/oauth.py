"""
@file oauth.py
@brief Pydantic schemas for OAuth2/OIDC provider management and exchange.

Covers provider CRUD, exchange code flow, and public provider list items.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, TypeAdapter, model_validator

from app.schemas.subgroup import SUBGROUP_ROLES

#: Community roles a group rule without subgroup_id may grant.
COMMUNITY_ROLES = ("viewer", "member", "admin")


class GroupMappingRule(BaseModel):
    """
    @brief One IdP group -> subgroup membership and/or community role rule.

    With subgroup_id the role must be a subgroup role; without it the role
    is a community role.
    """

    subgroup_id: UUID | None = None
    role: str = "member"

    @model_validator(mode="after")
    def _check_role(self) -> GroupMappingRule:
        """@brief Restrict role to the set valid for this rule kind."""
        allowed = SUBGROUP_ROLES if self.subgroup_id else COMMUNITY_ROLES
        if self.role not in allowed:
            raise ValueError(f"role must be one of {', '.join(allowed)}")
        return self


_RULES = TypeAdapter(dict[str, GroupMappingRule])


def validate_claim_mapping(value: dict[str, Any]) -> dict[str, Any]:
    """
    @brief Validate claim_mapping: string overrides plus optional group_mapping.

    @param value Raw claim_mapping.
    @return JSON-serialisable claim_mapping (group_mapping normalised).
    @throws ValueError On a non-string override or an invalid group rule.
    """
    out: dict[str, Any] = {}
    for key, val in value.items():
        if key == "group_mapping":
            rules = _RULES.validate_python(val)
            out[key] = {g: r.model_dump(mode="json") for g, r in rules.items()}
        elif isinstance(val, str):
            out[key] = val
        else:
            raise ValueError(f"claim_mapping.{key} must be a string")
    return out


#: Validated claim_mapping type for write schemas.
ClaimMapping = Annotated[dict[str, Any], AfterValidator(validate_claim_mapping)]


class OAuthProviderCreate(BaseModel):
    """
    @brief Payload for creating an OAuth provider.

    Required: slug, display_name, provider_type, client_id, client_secret.
    Optional: issuer, icon_url, scopes, endpoints, group_mappings, claims, etc.
    """

    slug: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    provider_type: str = Field(..., min_length=1, max_length=16)
    client_id: str = Field(..., min_length=1, max_length=256)
    client_secret: str = Field(..., min_length=1)
    issuer: str | None = None
    discovery_url: str | None = None
    claim_mapping: ClaimMapping = Field(default_factory=dict)
    icon_url: str | None = None
    scopes: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    jwks_uri: str | None = None
    end_session_endpoint: str | None = None
    group_mappings: dict[str, str] = Field(default_factory=dict)
    default_role: str = "member"
    group_claim: str = "groups"
    avatar_claim: str = "picture"
    sub_claim: str = "sub"
    email_claim: str = "email"
    name_claim: str = "name"
    enabled: bool = True
    auto_create_users: bool = True


class OAuthProviderUpdate(BaseModel):
    """
    @brief Payload for updating an OAuth provider.

    All fields optional for partial updates.
    """

    slug: str | None = None
    display_name: str | None = None
    provider_type: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    issuer: str | None = None
    discovery_url: str | None = None
    claim_mapping: ClaimMapping | None = None
    icon_url: str | None = None
    scopes: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    jwks_uri: str | None = None
    end_session_endpoint: str | None = None
    group_mappings: dict[str, str] | None = None
    default_role: str | None = None
    group_claim: str | None = None
    avatar_claim: str | None = None
    sub_claim: str | None = None
    email_claim: str | None = None
    name_claim: str | None = None
    enabled: bool | None = None
    auto_create_users: bool | None = None


class OAuthProviderResponse(BaseModel):
    """
    @brief Serialized OAuth provider for API responses.

    Excludes client_secret_encrypted for security.
    """

    id: UUID
    community_id: UUID
    slug: str
    display_name: str
    icon_url: str | None
    provider_type: str
    issuer: str | None
    discovery_url: str | None = None
    claim_mapping: dict[str, Any] = Field(default_factory=dict)
    client_id: str
    scopes: str
    authorization_endpoint: str | None
    token_endpoint: str | None
    userinfo_endpoint: str | None
    jwks_uri: str | None
    end_session_endpoint: str | None
    group_mappings: dict[str, str]
    default_role: str
    group_claim: str
    avatar_claim: str
    sub_claim: str
    email_claim: str
    name_claim: str
    enabled: bool
    auto_create_users: bool
    seeded_from_env: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OAuthExchangeRequest(BaseModel):
    """@brief Request body for exchanging OAuth callback code for tokens."""

    code: str = Field(..., min_length=1)


class OIDCProviderCreate(BaseModel):
    """@brief Payload for registering a generic OIDC provider via discovery."""

    slug: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    discovery_url: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1, max_length=256)
    client_secret: str = Field(..., min_length=1)
    scopes: str = "openid profile email"
    claim_mapping: ClaimMapping = Field(default_factory=dict)


class OIDCTestResult(BaseModel):
    """@brief Result of the admin discovery + sandbox token exchange test."""

    discovery_ok: bool
    issuer: str | None = None
    token_endpoint_reachable: bool = False
    error: str | None = None


class GroupMappingPreviewEntry(BaseModel):
    """@brief One configured group rule resolved against local subgroups."""

    group: str
    subgroup_id: str | None
    role: str | None
    subgroup_exists: bool | None
    matched: bool


class GroupMappingPreview(BaseModel):
    """@brief Sandbox preview of a provider group mapping (no writes)."""

    entries: list[GroupMappingPreviewEntry]
