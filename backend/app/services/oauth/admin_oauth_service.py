"""
@file admin_oauth_service.py
@brief Admin SSO provider service: CRUD, OIDC registration, test, preview, SSO-only.

Keeps repositories out of the admin routes. Mutations are audit logged.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import httpx
import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.core.valkey import DB_CACHE, get_pool
from app.models.oauth_provider import OAuthProvider
from app.repositories.audit_repo import AuditRepository
from app.repositories.oauth_repo import OAuthProviderRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.oauth import (
    OAuthProviderCreate,
    OAuthProviderUpdate,
    OIDCProviderCreate,
    OIDCTestResult,
)
from app.services.auth import sso_only
from app.services.oauth import sso_test_login
from app.services.oauth.discovery import DiscoveryEndpoints, discover_endpoints, fetch_discovery
from app.services.oauth.group_mapper import preview_group_mapping
from app.services.oauth.provider_rules import (
    invalid_discovery,
    slug_taken,
    trust_email_for,
    update_audit,
    username_claim_for,
)
from app.services.oauth.public_url import callback_url

logger = structlog.get_logger(__name__)


class AdminOAuthService:
    """@brief Admin operations on OAuth/OIDC providers for one community."""

    def __init__(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        settings: Settings,
        actor_id: uuid.UUID,
        ip: str | None,
    ) -> None:
        """
        @param db Request session.
        @param community_id Community scope.
        @param settings App settings (secret key, timeouts, base URL).
        @param actor_id Acting admin user id.
        @param ip Client IP for the audit log.
        """
        self._db = db
        self._cid = community_id
        self._settings = settings
        self._actor = actor_id
        self._ip = ip
        self._repo = OAuthProviderRepository(db)

    async def _audit(self, action: str, target_id: uuid.UUID, extra: dict[str, Any]) -> None:
        await AuditRepository(self._db).append(
            actor_id=self._actor,
            action=action,
            target_type="oauth_provider",
            target_id=target_id,
            extra_data=extra,
            ip_address=self._ip,
        )

    def _encrypt(self, secret: str) -> str:
        return encrypt_secret(secret, derive_fernet_key(self._settings.SECRET_KEY))

    async def _discover(self, discovery_url: str) -> tuple[DiscoveryEndpoints, str]:
        """
        @brief Fetch a discovery document: endpoints plus the exact issuer (ID token iss).

        @raises AppError 422 invalid_discovery.
        """
        try:
            doc = await fetch_discovery(discovery_url.strip(), self._settings.OIDC_HTTP_TIMEOUT)
        except (ValueError, httpx.HTTPError) as exc:
            raise invalid_discovery(exc) from exc
        keys = (
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "end_session_endpoint",
        )
        endpoints = cast(DiscoveryEndpoints, {k: doc[k] for k in keys if doc.get(k)})
        return endpoints, str(doc["issuer"])

    async def discover_issuer(self, issuer: str) -> DiscoveryEndpoints:
        """
        @brief OIDC discovery for an issuer URL.

        @raises AppError 422 invalid_discovery.
        """
        try:
            return await discover_endpoints(issuer.strip())
        except (ValueError, httpx.HTTPError) as exc:
            raise invalid_discovery(exc) from exc

    async def _ensure_slug_free(self, slug: str, keep: uuid.UUID | None = None) -> None:
        """@brief 409 sso_slug_taken when a live provider (other than ``keep``) has ``slug``."""
        existing = await self._repo.find_by_slug(self._cid, slug)
        if existing is not None and existing.id != keep:
            raise slug_taken()

    async def _persist(self, provider: OAuthProvider) -> OAuthProvider:
        """@brief Insert a provider; a lost slug race maps to 409 sso_slug_taken."""
        try:  # the request rolls back on the 409
            return await self._repo.create(provider)
        except IntegrityError as exc:
            raise slug_taken() from exc

    def callback_url(self, slug: str) -> str:
        """@brief Redirect URI the admin registers at the IdP."""
        return callback_url(self._settings, slug)

    async def start_test_login(self, provider_id: uuid.UUID) -> tuple[str, str]:
        """
        @brief Begin an admin test login (nothing is provisioned); audited.

        @return (IdP authorize URL for the popup, browser binding cookie value).
        """
        provider = await self.get(provider_id)
        if not provider.authorization_endpoint or not provider.token_endpoint:
            raise AppError(
                code="sso_test_unavailable",
                message=_("Provider has no authorization/token endpoint"),
                status_code=422,
            )
        valkey = get_pool(self._settings, DB_CACHE)
        started = await sso_test_login.start(valkey, self._settings, provider, self._actor)
        await self._audit("sso.test_login.started", provider.id, {"slug": provider.slug})
        return started

    async def read_test_result(self, result_id: str) -> dict[str, Any]:
        """@brief One-time read of this admin's test login result."""
        valkey = get_pool(self._settings, DB_CACHE)
        result = await sso_test_login.read_result(valkey, result_id, self._actor)
        if result is None:
            raise NotFoundError(message=_("Test result not found or expired"))
        return result

    async def get(self, provider_id: uuid.UUID) -> OAuthProvider:
        """@brief Fetch a provider or raise NotFoundError."""
        provider = await self._repo.get_by_id(provider_id, self._cid)
        if not provider:
            raise NotFoundError(message=_("OAuth provider not found"))
        return provider

    async def list_all(self) -> list[OAuthProvider]:
        """@brief List providers for the community."""
        items, _total = await self._repo.list(community_id=self._cid, limit=100)
        return list(items)

    async def create(self, body: OAuthProviderCreate) -> OAuthProvider:
        """@brief Create a provider, filling endpoints from OIDC discovery."""
        await self._ensure_slug_free(body.slug)
        endpoints: DiscoveryEndpoints = {}
        issuer = body.issuer
        if body.provider_type == "oidc" and body.discovery_url:
            endpoints, issuer = await self._discover(body.discovery_url)
        elif body.provider_type == "oidc" and body.issuer:
            endpoints = await self.discover_issuer(body.issuer)
        provider = OAuthProvider(
            community_id=self._cid,
            slug=body.slug,
            display_name=body.display_name,
            provider_type=body.provider_type,
            client_id=body.client_id,
            client_secret_encrypted=self._encrypt(body.client_secret),
            issuer=issuer,
            discovery_url=body.discovery_url.strip() if body.discovery_url else None,
            claim_mapping=body.claim_mapping,
            icon_url=body.icon_url,
            scopes=body.scopes or "openid profile email groups",
            authorization_endpoint=(
                body.authorization_endpoint or endpoints.get("authorization_endpoint")
            ),
            token_endpoint=body.token_endpoint or endpoints.get("token_endpoint"),
            userinfo_endpoint=body.userinfo_endpoint or endpoints.get("userinfo_endpoint"),
            jwks_uri=body.jwks_uri or endpoints.get("jwks_uri"),
            end_session_endpoint=(
                body.end_session_endpoint or endpoints.get("end_session_endpoint")
            ),
            group_mappings=body.group_mappings,
            default_role=body.default_role,
            preset=body.preset,
            allowed_domains=body.allowed_domains,
            required_group=body.required_group,
            username_claim=username_claim_for(body),
            sync_profile=body.sync_profile,
            trust_email=trust_email_for(body),
            enabled=body.enabled,
            auto_create_users=body.auto_create_users,
        )
        provider = await self._persist(provider)
        await self._audit("oauth.provider.created", provider.id, {"slug": provider.slug})
        logger.info("oauth_provider_created", provider_id=str(provider.id), slug=provider.slug)
        return provider

    async def register_oidc(self, body: OIDCProviderCreate) -> OAuthProvider:
        """@brief Register an OIDC provider from its discovery URL."""
        await self._ensure_slug_free(body.slug)
        try:
            doc = await fetch_discovery(
                body.discovery_url.strip(), self._settings.OIDC_HTTP_TIMEOUT
            )
        except (ValueError, httpx.HTTPError) as exc:
            raise invalid_discovery(exc) from exc
        provider = OAuthProvider(
            community_id=self._cid,
            slug=body.slug,
            display_name=body.display_name,
            provider_type="oidc",
            client_id=body.client_id,
            client_secret_encrypted=self._encrypt(body.client_secret),
            issuer=doc["issuer"],
            discovery_url=body.discovery_url.strip(),
            scopes=body.scopes,
            claim_mapping=body.claim_mapping,
            authorization_endpoint=doc["authorization_endpoint"],
            token_endpoint=doc["token_endpoint"],
            userinfo_endpoint=doc.get("userinfo_endpoint"),
            jwks_uri=doc.get("jwks_uri"),
            end_session_endpoint=doc.get("end_session_endpoint"),
        )
        provider = await self._persist(provider)
        await self._audit(
            "oauth.provider.created", provider.id, {"slug": provider.slug, "type": "oidc"}
        )
        return provider

    async def update(self, provider_id: uuid.UUID, body: OAuthProviderUpdate) -> OAuthProvider:
        """@brief Partially update a provider (blank secret keeps the stored one)."""
        provider = await self.get(provider_id)
        data = body.model_dump(exclude_unset=True)
        if data.get("slug") and data["slug"] != provider.slug:
            await self._ensure_slug_free(data["slug"], keep=provider.id)
        secret = data.pop("client_secret", None)
        if secret:
            data["client_secret_encrypted"] = self._encrypt(secret)
        extra: dict[str, Any] = {}
        new_url = (data.get("discovery_url") or "").strip()
        ptype = data.get("provider_type") or provider.provider_type
        if new_url and new_url != provider.discovery_url and ptype == "oidc":
            endpoints, issuer = await self._discover(new_url)
            for key, value in endpoints.items():
                if not data.get(key):  # explicit endpoints in the body win (as in create)
                    data[key] = value
            if issuer != provider.issuer:
                extra = {"issuer": {"old": provider.issuer, "new": issuer}}
            data.update({"issuer": issuer, "discovery_url": new_url})
        extra.update(update_audit(provider, data, bool(secret)))
        try:
            provider = await self._repo.update(provider, data)
        except IntegrityError as exc:
            raise slug_taken() from exc
        await self._audit("oauth.provider.updated", provider.id, {"slug": provider.slug, **extra})
        return provider

    async def delete(self, provider_id: uuid.UUID) -> None:
        """@brief Soft-delete a provider."""
        provider = await self.get(provider_id)
        await self._repo.soft_delete(provider)
        await self._audit("oauth.provider.deleted", provider_id, {"slug": provider.slug})

    async def toggle(self, provider_id: uuid.UUID) -> OAuthProvider:
        """@brief Flip a provider's enabled flag."""
        provider = await self.get(provider_id)
        provider = await self._repo.update(provider, {"enabled": not provider.enabled})
        await self._audit(
            "oauth.provider.toggled",
            provider.id,
            {"slug": provider.slug, "enabled": provider.enabled},
        )
        return provider

    async def preview_groups(
        self, provider_id: uuid.UUID, groups: list[str] | None
    ) -> list[dict[str, Any]]:
        """@brief Resolve the provider's group mapping (optionally for sample groups)."""
        provider = await self.get(provider_id)
        return await preview_group_mapping(
            SubgroupRepository(self._db), self._cid, provider.claim_mapping, groups
        )

    async def test(self, provider_id: uuid.UUID) -> OIDCTestResult:
        """
        @brief Test discovery and a sandbox token exchange.

        A dummy code is posted; a 400/401 from the token endpoint proves it is
        reachable and client auth is evaluated.
        """
        provider = await self.get(provider_id)
        s = self._settings
        if not provider.discovery_url:
            return OIDCTestResult(discovery_ok=False, error="Provider has no discovery_url")
        try:
            doc = await fetch_discovery(provider.discovery_url, s.OIDC_HTTP_TIMEOUT)
        except (ValueError, httpx.HTTPError) as exc:
            return OIDCTestResult(discovery_ok=False, error=str(exc))
        result = OIDCTestResult(discovery_ok=True, issuer=doc.get("issuer"))
        try:
            redirect_uri = callback_url(s, provider.slug)
            async with httpx.AsyncClient(timeout=s.OIDC_HTTP_TIMEOUT) as client:
                resp = await client.post(
                    doc["token_endpoint"],
                    data={
                        "grant_type": "authorization_code",
                        "code": "nexara-sandbox-test",
                        "redirect_uri": redirect_uri,
                        "client_id": provider.client_id,
                    },
                )
            result.token_endpoint_reachable = resp.status_code in (400, 401)
            if not result.token_endpoint_reachable:
                result.error = f"Unexpected token endpoint status {resp.status_code}"
        except httpx.HTTPError as exc:
            result.error = f"Token endpoint unreachable: {exc.__class__.__name__}"
        return result

    async def set_sso_only(self, enabled: bool) -> str | None:
        """@brief Toggle SSO-only mode; returns the lockout warning when enabled."""
        await sso_only.set_sso_only(self._db, self._cid, enabled, self._actor)
        await AuditRepository(self._db).append(
            actor_id=self._actor,
            action="settings.sso_only.updated",
            target_type="community",
            target_id=self._cid,
            extra_data={"enabled": enabled},
            ip_address=self._ip,
        )
        return sso_only.SSO_ONLY_WARNING if enabled else None
