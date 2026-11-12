"""
@file config.py
@brief Application configuration via environment variables.

All settings are loaded from environment variables (with optional .env file support).
Pydantic BaseSettings handles validation, type coercion, and defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    APP_BASE_URL: str = "http://localhost:8000"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = ""
    OIDC_HTTP_TIMEOUT: float = 10.0
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

    # --- VAPID (Web Push) ---
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""

    # --- SMTP ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

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

    # --- Rate Limiting ---
    RATE_LIMIT_DEFAULT: str = "600/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    @property
    def allowed_origins_list(self) -> list[str]:
        """@brief Parse comma-separated ALLOWED_ORIGINS into a list."""
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

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
