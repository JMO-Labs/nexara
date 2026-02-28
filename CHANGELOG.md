# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
