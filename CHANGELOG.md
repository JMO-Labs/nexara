# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Lists

#### Added
- Lists and list items, scoped by community, served under the `/lists` API prefix
- List templates: clone a template into a new list
- Signups on list items: members claim and release items
- List notifications (in-app, Web Push, email) via `NotificationService`
- Lists UI pages in the frontend (index, detail, template and signup views)
- Alembic migration `0019_list_templates` adding list template, list, member, item, signup and completion tables

### Phase 1.5 -- OAuth2/OIDC Multi-Provider

Replaces single-provider OIDC with a DB-backed, multi-provider OAuth2/OIDC
system. Admin-managed providers, Authlib token verification, and RP-initiated
logout.

### Added

#### Frontend
- Multi-provider OAuth login buttons on login page (dynamic from `/auth/config`)
- OAuth callback page with exchange-code flow and error handling
- Admin SSO provider management page (list, add, edit, delete, enable/disable)
- Admin SSO provider form with OIDC auto-discovery, group-to-role mapping, and claim configuration
- `useSsoProviderForm` composable for provider form state and actions
- Linked accounts placeholder component in user settings
- SSO tab in admin panel navigation
- RP-initiated logout support in auth store (redirects to IdP end-session URL)
- 30+ new i18n translation keys for OAuth/SSO UI

#### Backend
- Authlib dependency for OAuth2/OIDC flow and JWKS token verification
- `OAuthProvider` model with DB-backed provider configuration
- `UserOAuthLink` model for multi-provider user identity links
- Alembic migration for `oauth_providers` and `user_oauth_links` tables
- OAuth provider and user link repositories
- Fernet encryption utility for client secrets at rest
- OIDC auto-discovery service with SSRF protection
- Group-to-role mapper with priority ordering (admin > member > viewer)
- OAuth user provisioner for create, link, and update flows
- Provider manager with in-memory caching and env-var seeding
- Authlib-based OAuth flow (PKCE, authorize URL, code exchange)
- JWKS token verifier with cached key sets
- Pydantic schemas for provider CRUD, config, and exchange
- Public OAuth routes: login redirect, callback, exchange code
- Admin OAuth routes: provider CRUD, toggle, discover, test connection
- Startup hook to seed default provider from `OIDC_*` env vars
- Deprecated `/oidc/*` routes redirecting to `/oauth/{slug}/*`
- RP-initiated logout endpoint returning `end_session_url`

#### Types
- `OAuthProviderInfo`, `OAuthGroupMapping`, `OAuthProviderResponse` TypeScript types

### Security
- PKCE for all OAuth authorization flows
- SSRF protection on OIDC discovery (rejects private IPs and localhost)
- Fernet encryption for OAuth client secrets stored in DB
- Single-use exchange codes with 60s TTL in Valkey

## [0.1.0] - 2026-02-27

### Phase 1 -- Foundation and Core Experience

A fully functional, self-hosted community platform with authentication, activity
feed, media sharing, search, notifications, and admin panel.

### Added

#### Infrastructure (Group 1)
- PostgreSQL 16+ database with 37 tables via Alembic migrations
- Valkey (Redis-compatible) config with 3 logical DBs, connection pooling, health checks
- Storage abstraction layer with local filesystem and S3-compatible backends
- Docker Compose deployment with multi-stage Dockerfiles, supervisord, and Nginx
- Full-text search tsvector columns and GIN indexes on posts, users, events

#### Core Backend (Group 2)
- FastAPI application with layered architecture (routes, services, repositories, models)
- WAF middleware blocking SQL injection, path traversal, and malicious user agents
- Structured JSON logging with request ID correlation
- Prometheus metrics endpoint with 11 counters/gauges
- Health check endpoint with DB, Redis, and storage component status
- Celery task queue with Beat scheduler and advisory lock deduplication
- Rate limiting via SlowAPI with Valkey backend
- i18n support with gettext wrapper and en_US locale

#### Auth and Realtime (Group 3)
- Local registration and login with bcrypt password hashing
- RS256 JWT access tokens and opaque refresh tokens with replay detection
- OIDC/OAuth2 login with PKCE, group-to-role mapping, and user provisioning
- TOTP 2FA enrollment, verification, and backup codes
- RBAC with admin, member, and viewer roles
- Invite system with token-based registration and role assignment
- HaveIBeenPwned breach check (k-anonymity) during registration
- Password reset flow with token generation and email delivery
- WebSocket endpoint with first-message JWT auth and ping/pong heartbeat
- SSE notification stream with Bearer auth and Last-Event-ID support
- Connection manager with per-user tracking and Prometheus gauge updates
- Valkey pub/sub for real-time message routing
- Presence tracking via sorted-set with TTL and cleanup

#### Frontend Shell (Group 4)
- Nuxt 3 SPA with Tailwind CSS, Flowbite, and Pinia
- Pre-rendered landing page with hero, features, and install sections
- Activity feed with infinite scroll, Markdown rendering, and SSE updates
- Post detail page with threaded comments and reactions
- Login, registration, password reset, and 2FA pages
- Authenticated app layout with sidebar, top bar, bottom navigation, and toasts
- PWA manifest and service worker with app shell caching
- Dark mode with system preference detection and localStorage persistence
- Global auth middleware with route guards
- i18n with 100+ translation keys in en-US locale

#### Feature Components (Group 5)
- Photo upload with drag-drop, client validation, and progress bar
- Server-side thumbnail generation (Pillow, WebP, EXIF stripping)
- Media grid with responsive columns and full-size lightbox with keyboard nav
- In-app SSE notifications and email notifications via Celery
- Jinja2 email templates (notification, invite, password reset)
- Notification preferences (6x2 matrix with mute-all toggle)
- Community branding (name, logo, primary color) with CSS variable injection
- User settings pages (profile, account, security, notifications)
- Unified Postgres FTS search across posts, users, and events
- Admin dashboard with metrics cards, recent audit log, and WAF blocks
- Admin user management (role change, suspend, restore, delete)
- Admin invite management (create, list, revoke)
- Admin community settings (registration, invite requirement, WAF, storage quota)
- Admin audit log viewer with action filtering and cursor pagination
- Moderation schema with content_reports and user_blocks tables
- Block filter applied in base repository with bidirectional exclusion

### Security
- WAF middleware with pattern-based blocking and logging
- HIBP password breach checking on registration
- RS256 JWT with JWKS endpoint
- Refresh token replay detection with family revocation
- PKCE for OIDC authorization flow
- Security headers middleware (X-Content-Type-Options, X-Frame-Options, etc.)
- EXIF metadata stripping on uploaded photos
- DOMPurify sanitization on Markdown rendering

### Testing
- 634 backend unit tests (pytest + pytest-asyncio)
- 118 frontend unit/integration tests (Vitest + @vue/test-utils)
- TDD-first approach across all components

### Documentation
- README with quick start, tech stack, and development setup
- MkDocs Material documentation site (getting started, development, deployment)
- Doxygen-style comments on all files, classes, and public functions
- OpenAPI/ReDoc auto-generated API documentation
- CONTRIBUTING.md with code standards and merge request process
