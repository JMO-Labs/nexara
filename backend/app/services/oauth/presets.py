"""
@file presets.py
@brief Built-in SSO provider presets (discovery URL templates, scopes, claim mapping).

Presets prefill the admin provider form; they are data only. Public callback
URLs shown in help text are built from APP_BASE_URL by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Preset:
    """
    @brief One SSO provider preset.

    @param kind 'oidc' (discovery) or 'oauth2' (fixed endpoints).
    @param label Display name.
    @param discovery_url Template with {placeholders}; oidc only.
    @param params Placeholder names the admin must supply (with defaults in ``defaults``).
    @param scopes Space-separated scopes.
    @param claim_mapping Nexara field -> provider claim.
    @param username_claim Claim holding the username (applied on create).
    @param trust_email Default for the provider's trust_email (treat emails as
           verified); on only for self-hosted IdPs where users cannot edit their email.
    @param help Admin-facing setup hint.
    """

    kind: Literal["oidc", "oauth2"]
    label: str
    scopes: str
    help: str
    discovery_url: str | None = None
    params: tuple[str, ...] = ()
    defaults: dict[str, str] = field(default_factory=dict)
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    emails_endpoint: str | None = None
    claim_mapping: dict[str, Any] = field(default_factory=dict)
    username_claim: str = "preferred_username"
    trust_email: bool = False

    def to_dict(self, key: str) -> dict[str, Any]:
        """@brief JSON-serialisable form for the presets endpoint."""
        return {"key": key, **self.__dict__}

    def render_discovery_url(self, **values: str) -> str | None:
        """
        @brief Fill the discovery URL template.

        @param values Placeholder values (defaults fill gaps).
        @return URL, or None for presets without discovery.
        @raises KeyError when a required placeholder is missing.
        """
        if not self.discovery_url:
            return None
        return self.discovery_url.format(**{**self.defaults, **values})


_OIDC = "openid email profile"

PRESETS: dict[str, Preset] = {
    "authentik": Preset(
        kind="oidc",
        label="authentik",
        discovery_url="https://{host}/application/o/{slug}/.well-known/openid-configuration",
        params=("host", "slug"),
        scopes=_OIDC,
        claim_mapping={"groups": "groups"},
        trust_email=True,
        help="Create an OAuth2/OIDC provider + application. The default profile "
        "scope already includes the groups claim.",
    ),
    "keycloak": Preset(
        kind="oidc",
        label="Keycloak",
        discovery_url="https://{host}/realms/{realm}/.well-known/openid-configuration",
        params=("host", "realm"),
        scopes=_OIDC,
        claim_mapping={"groups": "groups"},
        trust_email=True,
        help="Add a 'Group Membership' mapper to the client so the groups claim "
        "is included in the ID token.",
    ),
    "authelia": Preset(
        kind="oidc",
        label="Authelia",
        discovery_url="https://{host}/.well-known/openid-configuration",
        params=("host",),
        scopes=f"{_OIDC} groups",
        claim_mapping={"groups": "groups"},
        trust_email=True,
        help="Allow the groups scope on the Authelia OIDC client.",
    ),
    "google": Preset(
        kind="oidc",
        label="Google",
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        scopes=_OIDC,
        help="Google does not provide group claims; use allowed domains instead.",
    ),
    "microsoft": Preset(
        kind="oidc",
        label="Microsoft",
        discovery_url="https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
        params=("tenant",),
        defaults={"tenant": "common"},
        scopes=_OIDC,
        claim_mapping={"groups": "groups", "email_verified": "xms_edov"},
        help="In the app registration's Token configuration add the optional claims "
        "'groups' and 'xms_edov' (email domain owner verified). Entra sends no "
        "email_verified claim, so without xms_edov new accounts cannot sign in.",
    ),
    "gitlab": Preset(
        kind="oidc",
        label="GitLab",
        discovery_url="https://{host}/.well-known/openid-configuration",
        params=("host",),
        defaults={"host": "gitlab.com"},
        scopes=_OIDC,
        claim_mapping={"groups": "groups"},
        help="Self-hosted GitLab: set host. Groups come from the 'groups' claim.",
    ),
    "github": Preset(
        kind="oauth2",
        label="GitHub",
        authorization_endpoint="https://github.com/login/oauth/authorize",
        token_endpoint="https://github.com/login/oauth/access_token",
        userinfo_endpoint="https://api.github.com/user",
        emails_endpoint="https://api.github.com/user/emails",
        scopes="read:user user:email read:org",
        claim_mapping={"sub": "id", "name": "name", "picture": "avatar_url"},
        username_claim="login",
        help="GitHub OAuth app. Only verified primary emails are trusted.",
    ),
    "discord": Preset(
        kind="oauth2",
        label="Discord",
        authorization_endpoint="https://discord.com/oauth2/authorize",
        token_endpoint="https://discord.com/api/oauth2/token",
        userinfo_endpoint="https://discord.com/api/users/@me",
        scopes="identify email",
        claim_mapping={"sub": "id", "name": "global_name"},
        username_claim="username",
        help="Discord application. The 'verified' flag gates email trust.",
    ),
    "custom": Preset(
        kind="oidc",
        label="Custom OIDC",
        discovery_url="{discovery_url}",
        params=("discovery_url",),
        scopes=_OIDC,
        trust_email=True,
        help="Any OIDC provider; paste its discovery URL.",
    ),
}
