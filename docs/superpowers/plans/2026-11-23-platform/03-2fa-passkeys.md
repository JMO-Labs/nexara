# PR 3 — 2FA + Passkeys

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Usable TOTP, recovery codes, passkeys (2FA + passwordless), admin policy.
**Spec:** `00-overview.md` (Q3, Q4). **Branch:** `feat/plat-3-2fa` from `feat/plat-2-apprise`. Task 1 → (2 ∥ 3) → 4 → 5.

---

### Task 1: Data + TOTP lifecycle backend

**Files:**
- Create: `backend/alembic/versions/0070_twofactor.py`, `backend/app/models/passkey.py`, `backend/app/services/auth/two_factor.py`, `backend/app/api/v1/auth_2fa.py` (move `/2fa/*` routes out of `auth.py`)
- Modify: `backend/app/models/user.py`, `backend/app/models/community.py`, `backend/app/repositories/user_repo.py` (`update_totp` can clear)
- Test: `backend/tests/unit/services/auth/test_two_factor.py`, `backend/tests/integration/api/test_auth_2fa.py`

**Interfaces:**
- Migration: encrypt existing `users.totp_secret` in place (Fernet); add `users.totp_pending_secret text`, `users.two_factor_required_since timestamptz`; `communities.require_2fa text check in ('off','admins','everyone') default 'off'`; table `passkeys(id, user_id, community_id, credential_id bytea unique, public_key bytea, sign_count int, transports text[], name text, created_at, last_used_at)`.
- Routes (`/api/v1/auth/2fa`): `POST /totp/start` → `{otpauth_uri, secret}` (pending); `POST /totp/confirm {code}` → enables, returns 10 recovery codes (deletes old); `POST /totp/disable {password|code}`; `POST /recovery/regenerate {code}` → 10 new codes; `GET /status` → `{totp, passkeys:int, recovery_left:int, required:bool, grace_until}`.
- Admin: `POST /api/v1/admin/users/{id}/reset-2fa` (clears TOTP, codes, passkeys; audit `admin.user.2fa_reset`); `PUT /api/v1/admin/security {require_2fa}`.
- Audit `2fa.enabled|disabled|recovery_regenerated` (actor = user).
- [ ] Tests: confirm with wrong code → 400, not enabled; disable requires valid password or code; regenerate invalidates old codes; admin reset clears all; secret column never plaintext after migration (decrypt round-trip).
- [ ] Implement → PASS → commit `feat(2fa): TOTP lifecycle, recovery codes, admin reset`

---

### Task 2: Passkeys backend

**Files:**
- Create: `backend/app/services/auth/passkeys.py`, `backend/app/api/v1/auth_passkeys.py`
- Modify: `backend/pyproject.toml` (`webauthn>=2.2`), `backend/app/core/config.py` (`WEBAUTHN_RP_ID` default host of `PUBLIC_URL`, `WEBAUTHN_ORIGIN` default `PUBLIC_URL`)
- Test: `backend/tests/unit/services/auth/test_passkeys.py`

**Interfaces:**
- Register (authenticated): `POST /api/v1/auth/passkeys/register/options` → options JSON (challenge in Valkey 5 min, `resident_key=preferred`, `user_verification=preferred`, exclude existing); `POST .../register/verify {credential, name}`.
- Login: `POST /api/v1/auth/passkeys/login/options {email?}` (empty allowCredentials when no email = discoverable); `POST .../login/verify {credential, pending_token?}` → with `pending_token` it completes 2FA step; without, passwordless login (passkey with UV counts as both factors). Records sign-in `method="passkey"`.
- `GET/PATCH/DELETE /api/v1/auth/passkeys[/{id}]` rename/remove; audit `passkey.added|removed`.
- Sign count must increase (or both 0) else reject `passkey_cloned`.
- [ ] Tests (use `webauthn` test vectors / mocked `verify_*_response`): wrong origin → 400; replayed challenge → 400; sign_count regression → 400; deleting other user's passkey → 404.
- [ ] Implement → PASS → commit `feat(auth): passkeys for sign-in and second factor`

---

### Task 3: Login enforcement (all paths)

**Files:**
- Modify: `backend/app/services/auth_service.py`, `backend/app/core/dependencies.py`, `backend/app/api/v1/oauth.py`
- Test: `backend/tests/integration/api/test_2fa_matrix.py`

**Interfaces:**
- `def second_factor_needed(user) -> bool` = `totp_enabled or passkeys>0` (passkeys count only if user chose "Use passkey as 2FA" — default true when any passkey).
- Policy: if `require_2fa` covers user and user has no factor → token claim `twofa_setup_required=true` + `grace_until = two_factor_required_since + 7d`; after grace, `get_current_user` returns 403 `2fa_setup_required` for all routes except `/auth/2fa/*`, `/auth/passkeys/register/*`, `/users/me`, `/auth/logout`.
- SSO login: never asks local 2FA; policy does not apply to SSO-only users (`password_hash IS NULL`).
- [ ] Matrix test: {password, magic_link} × {no 2FA, TOTP, passkey} → tokens only after second factor; recovery code works once; SSO with TOTP enabled → tokens directly; policy `everyone`, day 8 without factor → 403 on `/api/v1/posts`, 200 on `/api/v1/auth/2fa/status`.
- [ ] Implement → PASS → commit `feat(auth): enforce second factor on every login path`

---

### Task 4: Frontend security settings + login

**Files:**
- Create: `frontend/components/settings/SecurityTab.tsx`, `frontend/components/settings/security/{TotpSetup,RecoveryCodes,PasskeyList}.tsx`, `frontend/lib/api/twoFactor.ts`, `frontend/lib/passkeys.ts`, `frontend/components/admin/SecurityPolicy.tsx`
- Modify: `frontend/components/settings/SettingsTabs.tsx` (+Security), `frontend/app/(auth)/two-factor/page.tsx` (+"Use a passkey"), `frontend/app/(auth)/login/page.tsx` (+"Sign in with a passkey", `autocomplete="username webauthn"`), `frontend/components/admin/UsersTab.tsx` ("Reset 2FA"), `package.json` (`@simplewebauthn/browser`, `qrcode`)
- Test: `frontend/tests/unit/settings/SecurityTab.test.tsx`, `frontend/tests/unit/auth/passkeyLogin.test.tsx`

**Interfaces:**
- TOTP setup: QR (`qrcode.toDataURL(otpauth_uri)`, alt "QR code for authenticator app") + secret copy + 6-digit input `inputMode="numeric" autocomplete="one-time-code"`.
- Recovery codes: shown once, Copy + Download `.txt`, checkbox "I saved these" gates Done.
- Passkeys hidden with note "Passkeys need a secure (HTTPS) connection." when `!window.isSecureContext`.
- Grace banner in Shell: "Your admin requires two-step sign-in. Set it up by {date}." → Settings › Security.
- [ ] Tests: confirm flow shows 10 codes; insecure context hides passkey button; admin reset confirm dialog → POST.
- [ ] Implement → PASS → commit `feat(settings): security tab with authenticator, recovery codes, passkeys`

---

### Task 5: Polish PR 3
- [ ] Full suites + build; eval live script: TOTP via `pyotp` from script, recovery once, policy grace; passkeys verified behind user's HTTPS reverse proxy (ask user for hostname when reached; set `PUBLIC_URL`, `WEBAUTHN_RP_ID`); screenshots; PR "Platform 3: 2FA and passkeys".
