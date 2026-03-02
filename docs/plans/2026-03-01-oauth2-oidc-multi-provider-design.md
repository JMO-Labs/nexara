# OAuth2/OIDC Multi-Provider Design

> **Date:** 2026-03-01
> **Status:** Approved
> **Scope:** Replace single-provider OIDC with robust multi-provider OAuth2/OIDC system

---

## Problem Statement

The current OIDC implementation has critical gaps: single provider only, no id_token
signature verification, no admin UI for provider management, and a broken callback UX
(returns raw JSON). The system needs to support any OAuth2/OIDC provider (Authentik,
Google, GitHub, etc.) with easy admin setup and proper security.

---

## Decisions

| Decision | Choice |
|----------|--------|
| Library | Authlib (replaces python-jose for OIDC) |
| Provider count | Multiple simultaneous providers |
| Config source | Env vars seed a default provider; DB is source of truth; admin UI manages all |
| Discovery | Auto-discovery for OIDC; manual endpoint fallback for plain OAuth2 |
| Default role | Member (configurable per provider) |
| Token delivery | Exchange code pattern (no tokens in URLs) |
| Group mapping | Flexible JSON map (many IdP groups to Nexara roles) |
| Secret storage | Encrypted at rest (Fernet from SECRET_KEY) |
| Avatar | Pulled from configurable provider claim (default: "picture") |
| Logout | RP-initiated logout when provider supports end_session_endpoint |
| Smart card future | Pluggable auth strategy pattern; shared user provisioner/role mapper |

---

## Data Model

### New table: `oauth_providers`

Stores per-provider configuration. Each row is a fully independent OAuth2/OIDC
provider.

| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| community_id | int (FK) | Standard community scoping |
| slug | varchar(64) | URL-safe identifier (e.g., "authentik") |
| display_name | varchar(128) | Shown on login button |
| icon_url | text (nullable) | Optional icon for login button |
| provider_type | varchar(16) | "oidc" or "oauth2" |
| issuer | text (nullable) | OIDC issuer URL (for auto-discovery) |
| client_id | varchar(256) | OAuth2 client ID |
| client_secret_encrypted | text | Fernet-encrypted client secret |
| scopes | varchar(512) | Space-separated (default: "openid profile email groups") |
| authorization_endpoint | text (nullable) | Auto-populated or manual |
| token_endpoint | text (nullable) | Auto-populated or manual |
| userinfo_endpoint | text (nullable) | Auto-populated or manual |
| jwks_uri | text (nullable) | Auto-populated or manual |
| end_session_endpoint | text (nullable) | For RP-initiated logout |
| group_mappings | jsonb | {"idp-group": "nexara-role", ...} |
| default_role | varchar(32) | Fallback role (default: "member") |
| group_claim | varchar(64) | Claim key for groups (default: "groups") |
| avatar_claim | varchar(64) | Claim key for avatar (default: "picture") |
| sub_claim | varchar(64) | Claim key for subject (default: "sub") |
| email_claim | varchar(64) | Claim key for email (default: "email") |
| name_claim | varchar(64) | Claim key for name (default: "name") |
| enabled | boolean | Toggle without deleting |
| auto_create_users | boolean | Create users on first login (default: true) |
| seeded_from_env | boolean | Tracks env var origin |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Constraints:** unique on `(community_id, slug)`.

### New table: `user_oauth_links`

Links users to their OAuth provider identities. Replaces the single `users.oidc_sub`
column.

| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| user_id | int (FK) | FK to users |
| provider_id | int (FK) | FK to oauth_providers |
| sub | varchar(256) | User's "sub" claim from provider |
| email_from_provider | varchar(256, nullable) | Email as reported by provider |
| avatar_url | text (nullable) | Avatar from provider "picture" claim |
| raw_claims | jsonb (nullable) | Full claims for debugging/audit |
| linked_at | timestamptz | |

**Constraints:** unique on `(provider_id, sub)`.

### Migration from `users.oidc_sub`

1. Create the two new tables.
2. For each user with a non-null `oidc_sub`, create a `user_oauth_links` row pointing
   to the env-seeded provider.
3. Keep `users.oidc_sub` as nullable/deprecated for one release cycle, then drop.

---

## Backend Architecture

### Module structure

```
backend/app/services/oauth/
├── __init__.py
├── provider_manager.py       # Load/cache providers, env seeding
├── discovery.py              # .well-known/openid-configuration fetching
├── flow.py                   # Authorization code + PKCE (Authlib)
├── token_verifier.py         # JWKS-based id_token verification
├── user_provisioner.py       # Create/link/update users from claims
└── group_mapper.py           # Map IdP groups to Nexara roles

backend/app/api/v1/oauth.py              # /oauth/{slug}/login, /oauth/{slug}/callback, /oauth/exchange
backend/app/api/v1/admin/oauth.py        # Admin CRUD, test connection, discovery
backend/app/models/oauth_provider.py     # SQLAlchemy model
backend/app/models/user_oauth_link.py    # SQLAlchemy model
backend/app/schemas/oauth.py             # Pydantic request/response schemas
backend/app/repositories/oauth_repo.py   # DB queries for providers and links
```

### Login flow (`GET /api/v1/oauth/{slug}/login`)

1. Look up provider by slug (in-memory cache, 5-min TTL).
2. Build authorization URL via Authlib (PKCE S256, state, nonce).
3. Store state + code_verifier in a signed, short-lived cookie (10-min expiry).
4. Redirect user to IdP authorization endpoint.

### Callback flow (`GET /api/v1/oauth/{slug}/callback`)

1. Validate state from cookie matches callback state parameter.
2. Exchange authorization code for tokens via Authlib.
3. Verify id_token signature via JWKS (Authlib handles key rotation/caching).
4. Extract claims using configurable claim names (sub, email, name, groups, picture).
5. Map groups to Nexara role using `group_mappings` JSON.
6. Provision user: create new, link by email match, or update existing (avatar sync).
7. Generate a short-lived, single-use exchange code (stored in Valkey, 60s TTL).
8. Redirect to `{FRONTEND_URL}/auth/callback?code={exchange_code}`.

### Exchange endpoint (`POST /api/v1/oauth/exchange`)

1. Receive exchange code from frontend.
2. Look up in Valkey, delete immediately (single-use).
3. Return Nexara JWT access token + set refresh token cookie.

### Env var seeding (on startup)

`ProviderManager.seed_from_env()`:
1. If `OIDC_ISSUER` is set and no provider with `seeded_from_env=True` exists, create
   one using env vars (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_SCOPES`,
   `OIDC_ADMIN_GROUP`, `OIDC_MEMBER_GROUP`).
2. Run auto-discovery to populate endpoints.
3. If seeded provider already exists, skip (admin may have edited it via UI).

### Provider caching

Providers loaded from DB and cached in-memory with 5-minute TTL. Admin CRUD endpoints
flush the cache immediately via a cache-invalidation signal.

### Pluggable auth strategy (future smart card support)

The user provisioner and group/role mapper are designed as standalone services, not
coupled to OAuth. When smart card auth (mTLS/WebAuthn/FIDO2) is added, it will use
the same provisioner and mapper through a common interface:

```python
class AuthResult:
    """Common output from any auth strategy (OAuth, smart card, local)."""
    identity: str           # Unique identifier (sub, cert fingerprint, etc.)
    email: str | None
    display_name: str | None
    avatar_url: str | None
    groups: list[str]
    raw_claims: dict
```

---

## Frontend Design

### Login page

- `GET /api/v1/auth/config` returns `oauth_providers` list (slug, display_name,
  icon_url) alongside `local_auth_enabled`.
- Render one button per enabled provider, styled with display name and optional icon.
- Each button navigates to `/api/v1/oauth/{slug}/login` (full page redirect).

### Callback page (`/auth/callback`)

- New page at `frontend/pages/auth/callback.vue`.
- On mount, extract `code` query parameter.
- POST to `/api/v1/oauth/exchange` with the code.
- On success, store tokens in Pinia auth store, redirect to dashboard.
- On failure, show error message with link back to login.

### Admin UI: SSO Providers tab

New tab in admin settings (`frontend/pages/app/admin/settings.vue` or dedicated page):

1. **Provider list**: Table with name, type, enabled toggle, actions (edit, delete).
2. **Add provider wizard**:
   - Step 1: Type (OIDC / plain OAuth2).
   - Step 2: Issuer URL (OIDC) with "Discover" button, or manual endpoints (OAuth2).
   - Step 3: Client ID + Client Secret.
   - Step 4: Display name, slug (auto-generated), icon upload.
   - Step 5: Group-to-role mapping editor (dynamic key-value pairs).
   - Step 6: Advanced (scopes, claim names, default role, auto-create toggle).
3. **Test connection**: Opens popup, initiates test OAuth flow, reports result.
4. **Env-seeded badge**: Subtle indicator on providers created from env vars.

### User settings: Linked accounts

- In user profile/settings, new "Linked Accounts" section.
- Shows which OAuth providers the user is connected to (provider name + linked email).
- Allow linking additional providers or unlinking existing ones.

---

## Security

### Token verification

Authlib handles JWKS fetching, caching, rotation, and id_token signature verification.
This replaces the current `get_unverified_claims()` shortcut.

### Client secret encryption

Provider `client_secret` is encrypted at rest using Fernet symmetric encryption. The
encryption key is derived from the application `SECRET_KEY`. Decrypted only in memory
for token exchange.

### PKCE (S256)

Required for all providers. Authlib generates code_verifier and code_challenge
automatically.

### State parameter

Signed with HMAC, stored in a short-lived cookie (10 minutes), validated on callback.

### Exchange code

Short-lived (60s), single-use, stored in Valkey. Prevents tokens from appearing in
URLs or browser history.

### SSRF protection

Auto-discovery and JWKS fetching validate URLs are public HTTPS endpoints. Private
IPs, localhost, and non-HTTPS schemes are rejected.

### Rate limiting

OAuth login and callback endpoints use existing WAF rate-limiting middleware.

### Audit logging

All admin provider CRUD operations (create, edit, delete, toggle) write to the audit
log.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Provider not found (bad slug) | 404, redirect to login with error query param |
| Provider disabled | 403, redirect to login with "provider disabled" message |
| Discovery fails | Admin UI shows error; provider saveable with manual endpoints |
| Token exchange fails | Redirect to login with generic error; details in server logs |
| id_token verification fails | Redirect to login with generic error; details in server logs |
| No matching group, default_role = deny | Redirect to login with "access denied" message |
| Email conflict | Link if same email and unlinked; reject with "email registered" otherwise |
| Provider endpoint unreachable | Test connection shows specific error; login shows generic error |
| Exchange code expired/invalid | Frontend shows "session expired" with link to login |

---

## RP-Initiated Logout

When a user who logged in via OAuth logs out of Nexara:

1. Invalidate Nexara session (existing behavior).
2. If provider has `end_session_endpoint`, redirect to it with `id_token_hint`.
3. If no `end_session_endpoint`, log out locally only.

---

## Testing Strategy

### Unit tests

- ProviderManager: env seeding, cache TTL, provider lookup
- Discovery: parsing .well-known responses, malformed data, SSRF validation
- TokenVerifier: JWKS fetching, signature verification, expired tokens
- UserProvisioner: new user, email linking, avatar sync, conflict handling
- GroupMapper: multi-group mapping, default role fallback, empty groups

### Integration tests

- Full login/callback flow with mocked IdP responses
- Env var seeding with and without existing DB providers
- Admin CRUD with auto-discovery
- Exchange code flow (Valkey single-use)

### Security tests

- Reject unsigned/unverified id_tokens
- PKCE enforcement
- State mismatch rejection
- SSRF protection on discovery URLs
- Rate limiting on OAuth endpoints

### Migration test

- Verify `oidc_sub` data migrates to `user_oauth_links` correctly

---

## Dependencies

### Add

- `authlib>=1.3.0` — OAuth2/OIDC client, JWKS, auto-discovery
- `cryptography` — Already present (used by python-jose); needed by Authlib

### Remove (after migration)

- `python-jose[cryptography]` — Replaced by Authlib for OIDC; evaluate if still
  needed for Nexara's own JWT signing (may keep for that purpose)

---

## Env Vars

All existing OIDC env vars remain supported for backward compatibility and initial
seeding:

| Variable | Default | Purpose |
|----------|---------|---------|
| OIDC_ISSUER | "" | Issuer URL for env-seeded provider |
| OIDC_CLIENT_ID | "" | Client ID for env-seeded provider |
| OIDC_CLIENT_SECRET | "" | Client secret for env-seeded provider |
| OIDC_SCOPES | "openid profile email groups" | Scopes for env-seeded provider |
| OIDC_ADMIN_GROUP | "nexara-admin" | Admin group for env-seeded provider |
| OIDC_MEMBER_GROUP | "nexara-member" | Member group for env-seeded provider |

These env vars create a default provider on first startup. After that, the admin UI
is the primary management interface.
