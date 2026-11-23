# PR 4 — Deep SSO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Any OIDC/OAuth2 provider (Authentik first) with JIT rules and full profile/role/group sync.
**Spec:** `00-overview.md` (Q5, Q6, Q10). **Branch:** `feat/plat-4-sso` from `feat/plat-3-2fa`. Task 1 → (2 ∥ 3) → 4 → 5.

---

### Task 1: Consolidate + data

**Files:**
- Create: `backend/alembic/versions/0071_sso_sync.py`, `backend/app/services/oauth/presets.py`
- Modify: merge `backend/app/api/v1/oauth_admin.py` into `admin_oauth.py` (split by concern if >400 lines: `admin_oauth.py` CRUD, `admin_oauth_tools.py` discover/test/preview), `router.py`; `backend/app/models/oauth_provider.py`; `backend/app/models/subgroup.py` (`SubgroupMember.source`)
- Test: existing admin oauth tests moved/green; `backend/tests/unit/services/oauth/test_presets.py`

**Interfaces:**
- Provider columns: `preset text`, `allowed_domains text[] default '{}'`, `required_group text null`, `username_claim text default 'preferred_username'`, `sync_profile bool default true`. Drop per-column `*_claim` conflict: `claim_mapping` JSON is the single source; migration copies non-null `*_claim` columns into it then drops them.
- `subgroup_members.source text check in ('manual','sso') default 'manual'`.
- `PRESETS: dict[str, Preset]` with `kind ('oidc'|'oauth2')`, `discovery_url` template, `scopes`, `claim_mapping`, help text:
  - authentik: `https://{host}/application/o/{slug}/.well-known/openid-configuration`, scopes `openid email profile`, groups claim `groups` (authentik's default profile scope includes it).
  - keycloak: `https://{host}/realms/{realm}/.well-known/openid-configuration`, groups claim `groups` (needs mapper; help text says so).
  - authelia: `https://{host}/.well-known/openid-configuration`, scope `groups`.
  - google: `https://accounts.google.com/.well-known/openid-configuration`, no groups.
  - microsoft: `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration`, groups claim `groups`.
  - gitlab: `https://{host|gitlab.com}/.well-known/openid-configuration`, groups claim `groups`.
  - github: oauth2, authorize `https://github.com/login/oauth/authorize`, token `https://github.com/login/oauth/access_token`, user `https://api.github.com/user`, emails `https://api.github.com/user/emails`, scope `read:user user:email read:org`.
  - discord: oauth2, `https://discord.com/oauth2/authorize`, token `https://discord.com/api/oauth2/token`, user `https://discord.com/api/users/@me` (`verified` + `email`), scope `identify email`.
  - custom.
- [ ] Tests: migration copies `email_claim='mail'` into `claim_mapping.email`; every preset has required keys; `GET /api/v1/admin/oauth/presets` lists 9.
- [ ] Implement → PASS → commit `refactor(sso): single admin module, presets, claim mapping source of truth`

---

### Task 2: Provisioning rules + sync

**Files:**
- Modify: `backend/app/services/oauth/user_provisioner.py`, `backend/app/services/oauth/group_mapper.py`, `backend/app/services/oauth/flow.py` (OAuth2 email fetch), `backend/app/api/v1/oauth.py` (is_active before provisioning)
- Create: `backend/app/services/oauth/oauth2_email.py`
- Test: `backend/tests/unit/services/oauth/test_provisioning_rules.py`, `backend/tests/unit/services/oauth/test_group_sync.py`

**Interfaces:**
- Order in `provision(provider, claims)`: domain check (`email.split("@")[1].lower() in allowed_domains` when non-empty) → required group check → find by (provider, sub) → link by verified email → create only if `auto_create_users` else raise `AuthorizationError("sso_no_account")` → inactive/suspended → refuse `sso_account_disabled`.
- Refusal on returning user (domain/group no longer match) → also revoke all refresh tokens of that user.
- `sync_profile`: update display name, email (only if verified and not taken), avatar, username from `username_claim` (dedupe suffix `-2`…) on every login.
- `sync_subgroups(user, mapped_ids)`: add missing as `source='sso'`; delete `source='sso'` memberships not in `mapped_ids`; never touch `source='manual'`. Role sync unchanged but audit `sso.role_synced` when it changes.
- `async def fetch_verified_email(preset, access_token) -> str | None`: github → first `primary and verified` from `/user/emails`; discord → `email` if `verified`.
- [ ] Tests: domain `example.com` rejects `a@other.com`; required group missing → refused + tokens revoked; `auto_create_users=false` unknown user → `sso_no_account`; group dropped → sso membership removed, manual kept; name change synced; github unverified → no link; username `ruth` taken → `ruth-2`.
- [ ] Implement → PASS → commit `feat(sso): JIT rules, domain/group gates, full profile and group sync`

---

### Task 3: Login UX

**Files:**
- Modify: `frontend/components/auth/OAuthButtons.tsx` (brand glyph per preset, "Continue with {name}"), `frontend/app/(auth)/login/page.tsx` (error copy for `sso_no_account` "Your account isn't set up here yet. Ask an admin for an invite.", `sso_account_disabled`, domain/group "Your {provider} account isn't allowed to sign in here.")
- Test: `frontend/tests/unit/auth/OAuthButtons.test.tsx`
- [ ] Implement → PASS → commit `feat(auth): branded SSO buttons and clear SSO errors`

---

### Task 4: Admin provider editor

**Files:**
- Create: `frontend/components/admin/sso/{PresetPicker,ProviderRules,GroupMappingEditor,TestLoginPanel}.tsx`
- Modify: `frontend/components/admin/SsoProviderForm.tsx` (wizard: preset → connection → rules → mappings → test)
- Test: `frontend/tests/unit/admin/sso/*.test.tsx`

**Interfaces:**
- Shows callback URL to copy: `{PUBLIC_URL}/api/v1/auth/oauth/{slug}/callback`.
- Rules: auto-create toggle, default role, allowed domains (chips), required group, sync profile toggle.
- Mapping rows: provider group → role (`viewer|member|admin`) and/or Nexara groups (multi-select).
- Test login: opens popup with `?test=1`; backend returns claims + computed mapping (existing preview endpoint) without creating anything; panel renders raw claims JSON + "Would be: member of Smith Family, role member".
- [ ] Tests: picking Authentik prefills discovery template with host/slug inputs; mapping row saves to `claim_mapping.group_mapping`; test panel renders computed role.
- [ ] Implement → PASS → commit `feat(admin): SSO provider wizard with presets, rules, and group mapping`

---

### Task 5: Polish PR 4
- [ ] Full suites + build; live: Authentik in docker on eval network (`ghcr.io/goauthentik/server`, blueprint for app + groups `nexara-users`, `nexara-admins`, `smith-family`) → login, JIT create, role admin via group, remove from `smith-family` → membership gone next login, remove from `nexara-users` → refused; screenshots; PR "Platform 4: deep SSO".
