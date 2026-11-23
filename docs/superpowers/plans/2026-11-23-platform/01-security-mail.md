# PR 1 — Security fixes, Email, Sign-in log

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Close known holes, make email actually send (Gmail first), record every sign-in.
**Spec:** `00-overview.md` (Q1, Q10, Q11). **Branch:** `feat/plat-1-mail` from `feat/eng-w5-access`. Tasks 1–3 parallel; 4 after 2 (shares migration 0068).

---

### Task 1: Security fixes

**Files:**
- Modify: `backend/app/services/auth_service.py` (`enroll_2fa`, `verify_magic_link`), `backend/app/services/push_service.py:95` (`unsubscribe`), `backend/app/api/v1/auth.py` (rate limits)
- Delete: `backend/app/services/oidc_service.py` + its tests (unreferenced; unverified id_token decode)
- Test: `backend/tests/unit/services/test_auth_security_fixes.py`, `backend/tests/unit/services/test_push_service.py`

**Interfaces:**
- `enroll_2fa(user, current_code: str | None)` — when `user.totp_enabled`, raise `AuthorizationError("2fa_already_enabled")`; re-enroll only via Task 3.2 flow. Enroll stores pending secret without touching `totp_enabled`.
- `verify_magic_link` → if `user.totp_enabled` return `{"two_factor_required": True, "pending_token": ...}` exactly like password login (`auth_service.py:138`).
- `unsubscribe(user_id, endpoint)` deletes only `WHERE user_id = :user_id AND endpoint = :endpoint`.
- `@limiter.limit("10/minute")` on `/2fa/login`; reject reuse of the same TOTP code within its 30 s window (Valkey key `totp:used:{user_id}:{code}` TTL 90 s).
- [ ] Tests: enroll while enabled → 403 and `totp_enabled` unchanged; magic link for 2FA user returns `two_factor_required`; user B unsubscribing A's endpoint deletes 0 rows; same TOTP code twice → second 401; 11th `/2fa/login` in a minute → 429.
- [ ] Run (FAIL) → implement → PASS → commit `fix(auth): close 2FA bypasses and cross-user push unsubscribe`

---

### Task 2: SMTP admin settings + one sender

**Files:**
- Create: `backend/alembic/versions/0068_mail_signin.py` (mail part), `backend/app/services/email/smtp_settings.py`, `backend/app/api/v1/admin_email.py`, `backend/app/schemas/admin_email.py`, `frontend/components/admin/EmailTab.tsx`, `frontend/lib/api/adminEmail.ts`
- Modify: `backend/app/services/email/sender.py` (single sender), `backend/app/tasks/email_tasks.py` (use sender; delete smtplib path), `backend/app/models/community.py`, `frontend/components/admin/adminNav.ts`
- Test: `backend/tests/unit/services/email/test_sender.py`, `backend/tests/integration/api/test_admin_email.py`, `frontend/tests/unit/admin/EmailTab.test.tsx`

**Interfaces:**
- Columns on `communities`: `smtp_host text`, `smtp_port int`, `smtp_security text check in ('starttls','ssl','none')`, `smtp_user text`, `smtp_password text` (Fernet), `smtp_from text`, `smtp_from_name text`, `smtp_auth text check in ('password','google_oauth') default 'password'`, `smtp_google_refresh text` (Fernet), `smtp_last_ok_at timestamptz`, `smtp_last_error text`.
- `async def resolve_smtp(session, community_id) -> SmtpConfig | None` — DB row wins when `smtp_host` set, else env `SMTP_*` (security inferred: 465→ssl, else starttls). `SmtpConfig` dataclass(host, port, security, user, password, from_addr, from_name, auth, google_refresh).
- `send_email(cfg: SmtpConfig, to, subject, html, text) -> None`: aiosmtplib with `use_tls = security=="ssl"`, `start_tls = security=="starttls"`; password `.replace(" ", "")` when host is `smtp.gmail.com`. Updates `smtp_last_ok_at` / `smtp_last_error` (truncated 300 chars, no secrets).
- API: `GET/PUT /api/v1/admin/email` (returns `has_password`, never password), `POST /api/v1/admin/email/test {to}` → `{ok, error}`; audit `email.settings.updated`.
- Presets (frontend constant): Gmail `smtp.gmail.com 587 starttls` + help link `https://myaccount.google.com/apppasswords`, Outlook `smtp.office365.com 587 starttls`, Custom.
- [ ] Tests: port 587 starttls → aiosmtplib called `start_tls=True, use_tls=False`; 465 ssl → `use_tls=True`; Gmail password `"abcd efgh ijkl mnop"` sent as `"abcdefghijklmnop"`; GET never contains password; non-admin PUT → 403; test send failure returns `{ok:false,error}` and stores `smtp_last_error`; EmailTab Gmail preset fills host/port/security.
- [ ] Implement → PASS → commit `feat(email): admin SMTP settings with Gmail preset and test send`

---

### Task 3: Gmail via Google account (XOAUTH2) + real invite/reset mail

**Files:**
- Create: `backend/app/services/email/google_oauth.py`, `backend/templates/email/{invite,password_reset}.html`
- Modify: `backend/app/api/v1/admin_email.py` (+connect/callback), `backend/app/tasks/email_tasks.py` (`send_invite_email`, `send_password_reset_email` real), `EmailTab.tsx` ("Connect Google account")
- Test: `backend/tests/unit/services/email/test_google_oauth.py`, `backend/tests/unit/tasks/test_email_tasks.py`

**Interfaces:**
- Env `GOOGLE_MAIL_CLIENT_ID`, `GOOGLE_MAIL_CLIENT_SECRET` (admin may also enter in tab; stored Fernet). Scope `https://mail.google.com/`, `access_type=offline`, `prompt=consent`.
- `GET /api/v1/admin/email/google/start` → redirect URL (state in Valkey 10 min); `GET /api/v1/admin/email/google/callback` stores refresh token, sets `smtp_auth='google_oauth'`, host `smtp.gmail.com:587 starttls`, `smtp_user` = Google email.
- `async def google_access_token(cfg) -> str` (POST `https://oauth2.googleapis.com/token`, cache in Valkey until expiry-60 s); sender uses `aiosmtplib` `login` with XOAUTH2 string `base64("user=" + u + "\x01auth=Bearer " + t + "\x01\x01")` via `smtp.auth_xoauth2` if available else `execute_command(b"AUTH", b"XOAUTH2", ...)`.
- Invite mail: subject `"{inviter} invited you to {community}"`, button → `{PUBLIC_URL}/invite/{token}`. Reset: subject `"Reset your {community} password"`, link valid 60 min.
- [ ] Tests: token refresh cached; XOAUTH2 string exact; invite task calls `send_email` with link containing token; reset task same; missing SMTP → task logs `email.not_configured` and returns `"skipped"`.
- [ ] Implement → PASS → commit `feat(email): Gmail XOAUTH2 and real invite/reset emails`

---

### Task 4: Sign-in log (data only; UI in PR 6)

**Files:**
- Create: `backend/app/models/signin_event.py`, `backend/app/repositories/signin_repo.py`, `backend/app/services/auth/signin_log.py`
- Modify: migration 0068 (table), `auth_service.py` (password, 2FA, magic link), `api/v1/oauth.py` (SSO exchange), retention service (90 days)
- Test: `backend/tests/unit/services/auth/test_signin_log.py`, `backend/tests/integration/api/test_signin_events.py`

**Interfaces:**
- Table `signin_events(id uuid pk, community_id, user_id null, email_tried text, method text check in ('password','totp','recovery','passkey','magic_link','sso'), success bool, reason text null, ip inet, user_agent text, device text, created_at)`; index `(community_id, created_at desc)`, `(ip, created_at)`.
- `async def record_signin(session, *, community_id, user_id, email, method, success, reason, request) -> SigninEvent` — `device` = `"{browser} on {os}"` parsed by tiny regex table (Chrome/Firefox/Safari/Edge × Windows/macOS/iOS/Android/Linux), else `"Unknown device"`.
- `async def is_new_device(user_id, device, ip) -> bool` (no success in 90 days with same device string). On success + new device → `notify(user, "new_signin", {device, ip})`; add `new_signin` to `PREF_MAP` (in-app + email default on).
- Failure burst: `count_failures(ip, minutes=10) >= 10` → enqueue `admin_alert("signin_burst", {ip})` (Task 6.3 defines sender; until then log `security.signin_burst`).
- [ ] Tests: wrong password records `success=False, reason="bad_password"`; SSO success records `method="sso"`; UA Safari iPhone → `"Safari on iOS"`; second login same device → no `new_signin` notification; 10 failures same IP → burst logged once per 10 min.
- [ ] Implement → PASS → commit `feat(auth): record sign-in events and alert on new devices`

---

### Task 6: Gravatar email (user request 2026-11-23)

**Files:**
- Modify: migration 0068 (`user_settings.gravatar_email text null`), `backend/app/models/user_settings.py`, `backend/app/schemas/profile.py` / settings schemas, `backend/app/services/settings_service.py:130-140`, `backend/app/services/user_service.py` (`gravatar_url`, avatar fallback ~229-243), `frontend/components/settings/AvatarPicker.tsx`, `frontend/lib/api/settings.ts`
- Test: settings service unit test, AvatarPicker vitest

**Interfaces:**
- `gravatar_email` (≤254 chars, validated `EmailStr`, stored lowercased/stripped; empty string → null). Private: never returned except to the owner via `/settings/`.
- Hash source = `gravatar_email or user.email` everywhere (opt-in URL and fallback).
- Saving a new `gravatar_email` while the avatar is Gravatar-managed (`is_gravatar(avatar_url)`) recomputes `avatar_url`; uploaded photo untouched.
- UI: under the "Use Gravatar" toggle, input "Gravatar email" (`type="email"`, placeholder = login email, help "Use a different email for your Gravatar picture. Only you see this.").
- [ ] Tests: gravatar_email set → avatar URL hash = sha256 of it; cleared → login email hash; uploaded avatar unchanged on change; invalid email → 422; public profile response has no gravatar_email.
- [ ] Implement → PASS → commit `feat(settings): separate Gravatar email`

---

### Task 5: Polish PR 1
- [ ] Full suites + `next build`; eval rebuild; live: configure Gmail preset with fake creds → test shows readable error; invite sends via MailHog-style `aiosmtpd` sink container (`python -m aiosmtpd -n -l 0.0.0.0:1025`); screenshots EmailTab desktop + phone; open PR "Platform 1: security fixes, email, sign-in log" on base `feat/eng-w5-access`.
