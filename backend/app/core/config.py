"""
@file config.py
@brief Application configuration via environment variables.

All settings are loaded from environment variables (with optional .env file support).
Pydantic BaseSettings handles validation, type coercion, and defaults.
"""

import ipaddress
from functools import cached_property, lru_cache
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "http://localhost:8000"


class Settings(BaseSettings):
    """
    @brief Central application settings.

    Reads from environment variables (case-insensitive).
    Defaults are tuned for local development; production values
    come from the container environment or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Nexara"
    APP_BASE_URL: str = DEFAULT_BASE_URL
    """
    @brief External URL members open (links in emails, push, WebAuthn origin/RP id).
    Empty means the dev default; production must set it.
    """
    GRAFANA_URL: str = ""
    """@brief Optional admin link to a Grafana dashboard (http/https only)."""
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = ""
    OIDC_HTTP_TIMEOUT: float = 10.0
    OAUTH_ALLOW_INSECURE_DISCOVERY: bool = False
    """@brief Dev/eval only: allow http and private/localhost hosts in OIDC discovery."""
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # --- Valkey / Redis ---
    REDIS_URL: str = "redis://127.0.0.1:6379"

    # --- Storage ---
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "/data/media"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "nexara"

    # --- AI ('anthropic' | 'openai' | 'ollama'; empty disables AI) ---
    AI_PROVIDER: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Amazon Creators API (official product data; optional). Credentials come
    # from Associates Central > Creators API. Token URL depends on the region
    # the credentials were issued for (NA: api.amazon.com, EU: api.amazon.co.uk,
    # FE: api.amazon.co.jp).
    AMAZON_CREATORS_CLIENT_ID: str = ""
    AMAZON_CREATORS_CLIENT_SECRET: str = ""
    AMAZON_PARTNER_TAG: str = ""
    AMAZON_TOKEN_URL: str = "https://api.amazon.com/auth/o2/token"
    AMAZON_MARKETPLACE: str = "www.amazon.com"
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "llama2"
    AI_HTTP_TIMEOUT: float = 60.0
    #: User id of the Sassybot bot account (empty disables Sassybot comments)
    SASSYBOT_USER_ID: str = ""

    AI_DAILY_BUDGET_CENTS: int = 100
    AI_BUDGET_RESET_HOUR: int = 0

    # --- VAPID (Web Push) ---
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_SUBJECT: str = ""

    # --- FCM (native mobile push); unset disables the channel ---
    FCM_CREDENTIALS_FILE: str | None = None

    # --- SMTP ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    # Google OAuth client for "Connect Google account" mail (XOAUTH2); admin may override.
    GOOGLE_MAIL_CLIENT_ID: str = ""
    GOOGLE_MAIL_CLIENT_SECRET: str = ""

    # --- Auth / JWT ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = "/data/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "/data/jwt_public.pem"
    PASSWORD_MIN_LENGTH: int = 12
    HIBP_CHECK_ENABLED: bool = True
    TWO_FA_ISSUER: str = "Nexara"

    # --- OIDC ---
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_ADMIN_GROUP: str = "nexara-admin"
    OIDC_MEMBER_GROUP: str = "nexara-member"
    OIDC_SCOPES: str = "openid profile email groups"

    # --- Registration ---
    ENABLE_REGISTRATION: bool = True
    REQUIRE_INVITE: bool = False
    INVITE_EXPIRE_DAYS: int = 7
    STORAGE_QUOTA_DEFAULT: int = 10737418240

    # --- Community ---
    COMMUNITY_ID: str = "00000000-0000-0000-0000-000000000001"
    BIRTHDAY_AUTO_POST: bool = False

    # --- Subgroups ---
    MAX_SUBGROUP_MEMBERSHIPS_PER_USER: int = 5

    # --- Calendar subscriptions ---
    CALENDAR_SUBS_PER_USER_MAX: int = 10

    # --- WAF ---
    WAF_ENABLED: bool = True

    # --- Metrics ---
    ENABLE_METRICS: bool = True

    # --- Cloudflare Access ---
    CF_ACCESS_ENABLED: bool = False
    CF_ACCESS_TEAM_DOMAIN: str = ""

    # --- Reverse proxies ---
    TRUSTED_PROXIES: str = "127.0.0.1/32,::1/128"
    """
    @brief Comma-separated IPs/CIDRs whose X-Forwarded-For / X-Real-IP /
    CF-Connecting-IP are believed (bundled nginx = loopback). Add your outer
    reverse proxy, ingress pod CIDR or cloudflared address. ``*`` is NOT
    supported. Do not set uvicorn's FORWARDED_ALLOW_IPS wider than this.
    """

    # --- Rate Limiting ---
    RATE_LIMIT_DEFAULT: str = "600/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # --- WebAuthn (passkeys) ---
    WEBAUTHN_RP_ID: str = ""
    """@brief Relying-party id; defaults to the hostname of APP_BASE_URL."""
    WEBAUTHN_ORIGIN: str = ""
    """@brief Comma-separated expected origins; defaults to the APP_BASE_URL origin."""

    # --- Webhooks ---
    WEBHOOK_ALLOWED_HOSTS: str = ""
    """@brief Comma-separated hosts exempt from the SSRF guard (LAN targets)."""

    @field_validator("APP_BASE_URL")
    @classmethod
    def _default_base_url(cls, v: str) -> str:
        """@brief Empty (e.g. compose ``${APP_BASE_URL:-}``) falls back to the dev default."""
        return v.strip().rstrip("/") or DEFAULT_BASE_URL

    @property
    def base_url_unset(self) -> bool:
        """@brief True while APP_BASE_URL is still the dev default."""
        return self.APP_BASE_URL == DEFAULT_BASE_URL

    @field_validator("TRUSTED_PROXIES")
    @classmethod
    def _validate_trusted_proxies(cls, v: str) -> str:
        """@brief Fail at startup on an unparseable TRUSTED_PROXIES entry."""
        for item in v.split(","):
            if item.strip():
                ipaddress.ip_network(item.strip(), strict=False)
        return v

    @cached_property
    def trusted_proxy_networks(self) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
        """@brief Parsed TRUSTED_PROXIES networks."""
        return tuple(
            ipaddress.ip_network(x.strip(), strict=False)
            for x in self.TRUSTED_PROXIES.split(",")
            if x.strip()
        )

    @property
    def allowed_origins_list(self) -> list[str]:
        """@brief Parse comma-separated ALLOWED_ORIGINS into a list."""
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def webauthn_rp_id(self) -> str:
        """@brief Effective WebAuthn RP id (explicit setting, else APP_BASE_URL hostname)."""
        return self.WEBAUTHN_RP_ID.strip() or urlsplit(self.APP_BASE_URL).hostname or "localhost"

    @property
    def webauthn_origins(self) -> list[str]:
        """
        @brief Effective expected origins: explicit WEBAUTHN_ORIGIN list, else the
        APP_BASE_URL origin plus every ALLOWED_ORIGINS entry.
        """
        explicit = [o.strip().rstrip("/") for o in self.WEBAUTHN_ORIGIN.split(",") if o.strip()]
        if explicit:
            return explicit
        u = urlsplit(self.APP_BASE_URL)
        out = [f"{u.scheme}://{u.netloc}"]
        for o in self.allowed_origins_list:
            o = o.rstrip("/")
            if o and o != "*" and o not in out:
                out.append(o)
        return out

    @property
    def webhook_allowed_hosts(self) -> frozenset[str]:
        """@brief Parse WEBHOOK_ALLOWED_HOSTS into a lower-cased set."""
        return frozenset(
            h.strip().lower() for h in self.WEBHOOK_ALLOWED_HOSTS.split(",") if h.strip()
        )

    @property
    def celery_broker_url(self) -> str:
        """@brief Celery broker URL (Valkey DB 0)."""
        return f"{self.REDIS_URL}/0"

    @property
    def redis_pubsub_url(self) -> str:
        """@brief Pub/Sub connection URL (Valkey DB 1)."""
        return f"{self.REDIS_URL}/1"

    @property
    def redis_cache_url(self) -> str:
        """@brief Cache connection URL (Valkey DB 2)."""
        return f"{self.REDIS_URL}/2"

    @property
    def sync_database_url(self) -> str:
        """@brief Synchronous DB URL for Celery Beat advisory lock (psycopg2)."""
        return self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """
    @brief Factory function for Settings.

    Returns a cached singleton in production; tests can override
    this via FastAPI dependency injection.
    """
    return Settings()
