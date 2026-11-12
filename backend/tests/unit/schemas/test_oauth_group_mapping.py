"""
@file test_oauth_group_mapping.py
@brief Validation of claim_mapping.group_mapping on OAuth provider schemas.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.oauth import OAuthProviderCreate, OAuthProviderUpdate, OIDCProviderCreate

BASE = {
    "slug": "kc",
    "display_name": "Keycloak",
    "provider_type": "oidc",
    "client_id": "c",
    "client_secret": "s",
}
OIDC = {
    "slug": "kc",
    "display_name": "Keycloak",
    "discovery_url": "https://kc.example.com/.well-known/openid-configuration",
    "client_id": "c",
    "client_secret": "s",
}


def _build(cls, cm):
    if cls is OAuthProviderCreate:
        return cls(**BASE, claim_mapping=cm)
    if cls is OIDCProviderCreate:
        return cls(**OIDC, claim_mapping=cm)
    return cls(claim_mapping=cm)


SCHEMAS = [OAuthProviderCreate, OAuthProviderUpdate, OIDCProviderCreate]


@pytest.mark.parametrize("cls", SCHEMAS)
class TestGroupMappingValidation:
    """@brief group_mapping rules are validated on every write schema."""

    def test_valid_rules_accepted_and_serialised(self, cls):
        sid = uuid4()
        cm = {
            "email": "mail",
            "group_mapping": {
                "eng": {"subgroup_id": str(sid), "role": "moderator"},
                "ops": {"role": "admin"},
            },
        }
        out = _build(cls, cm).claim_mapping
        assert out["email"] == "mail"
        assert out["group_mapping"]["eng"] == {"subgroup_id": str(sid), "role": "moderator"}
        assert out["group_mapping"]["ops"] == {"subgroup_id": None, "role": "admin"}

    def test_subgroup_role_outside_subgroup_roles_rejected(self, cls):
        cm = {"group_mapping": {"eng": {"subgroup_id": str(uuid4()), "role": "admin"}}}
        with pytest.raises(ValidationError):
            _build(cls, cm)

    def test_global_role_outside_community_roles_rejected(self, cls):
        cm = {"group_mapping": {"ops": {"subgroup_id": None, "role": "owner"}}}
        with pytest.raises(ValidationError):
            _build(cls, cm)

    def test_bad_subgroup_id_rejected(self, cls):
        cm = {"group_mapping": {"eng": {"subgroup_id": "nope", "role": "member"}}}
        with pytest.raises(ValidationError):
            _build(cls, cm)

    def test_typo_role_rejected(self, cls):
        cm = {"group_mapping": {"eng": {"subgroup_id": str(uuid4()), "role": "membr"}}}
        with pytest.raises(ValidationError):
            _build(cls, cm)

    def test_non_string_claim_override_rejected(self, cls):
        with pytest.raises(ValidationError):
            _build(cls, {"email": 5})


def test_update_none_claim_mapping_allowed():
    assert OAuthProviderUpdate().claim_mapping is None
