# Platform Phase — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Nexara production-ready for real families: working email (Gmail), Apprise, 2FA + passkeys, deep SSO (Authentik first, any OIDC/OAuth2), installable mobile PWA with real OS notifications, admin monitoring/audit, onboarding, age groups and NSFW gating.

**Architecture:** Seven stacked PRs on `feat/eng-w5-access` (#390). Finish half-built systems before adding new ones (TOTP, OAuth provisioner, Apprise, push, audit log, `is_nsfw` all exist partially). Secrets in DB use the existing Fernet helper (`services/email_reply_admin_service.py` pattern, key from SECRET_KEY). All new admin changes write `AuditLog`.

**Tech Stack:** FastAPI, async SQLAlchemy 2, Alembic, Celery, Postgres 16, Valkey, aiosmtplib, apprise, pyotp, authlib, **new:** `webauthn` (py_webauthn ≥2.2), `@simplewebauthn/browser` ≥13, `qrcode` (frontend `qrcode` npm ≥1.5) for TOTP QR, `psutil` ≥6 (container CPU/mem). Next 16 / React 19, TanStack Query, Tailwind v4, Vitest, pytest.

**Spec:** grilling decisions Q1–Q19 (2026-11-23), recorded below.

## Files

| File | PR | Branch |
|---|---|---|
| `01-security-mail.md` | 1: security fixes, SMTP admin + Gmail, real invite/reset mail, sign-in log | `feat/plat-1-mail` |
| `02-apprise.md` | 2: Apprise UI, admin targets, SSRF guard | `feat/plat-2-apprise` |
| `03-2fa-passkeys.md` | 3: TOTP UI, recovery codes, passkeys, 2FA policy | `feat/plat-3-2fa` |
| `04-sso.md` | 4: provider presets, JIT rules, group sync, admin mapping UI | `feat/plat-4-sso` |
| `05-pwa-notify.md` | 5: PWA install/offline/update, push devices, OS notifications, badge | `feat/plat-5-pwa` |
| `06-monitoring.md` | 6: System page, disk, sign-in log UI, audit upgrades, admin alerts | `feat/plat-6-monitor` |
| `07-onboarding-age.md` | 7: onboarding wizard, age groups + suggestions, NSFW gating | `feat/plat-7-onboard` |
| `08-countdowns.md` | 8: countdowns (scoped, feed card, follow, Home strip, reminders, yearly) | `feat/plat-8-countdowns` |
| `09-plugin-core.md` | 9: plugin core contract (spec P1) — replaces old in-process plugin system | `feat/plat-9-plugins` |
| `10-plugin-host.md` | 10: plugin-host sandbox + compose/Helm (spec P2) | `feat/plat-10-host` |
| `11-sassybot.md` | 11: Sassybot as plugin in public repo `JMO-Labs/nexara-sassybot`; remove core Sassybot (spec P3) | `feat/plat-11-sassybot` |
| `12-marketplace.md` | 12: registry repo `JMO-Labs/nexara-plugins` (public), index, ratings, Marketplace/Sources tabs (spec P4) | `feat/plat-12-market` |

Each branch starts from the previous one. Each PR ends with a polish task: full suites + `npx next build`, eval rebuild, live script, phone-width screenshots (LAN 192.168.1.196:8090), a11y check.

## Decisions (spec)

- **Q1 Email:** admin Email tab; presets Gmail (`smtp.gmail.com:587` STARTTLS + app-password help), Outlook (`smtp.office365.com:587`), Custom; security `starttls|ssl|none`; password Fernet in DB; env vars remain fallback; "Send test email"; real invite + password-reset emails.
- **Q10 Google:** both — Gmail sending may use "Connect Google account" (XOAUTH2, refresh token stored encrypted) as alternative to app password; "Sign in with Google" is an SSO preset (Q6).
- **Q2 Apprise:** member UI in Settings › Notifications "Other apps" (add/test/remove, hints for ntfy, Discord, Telegram, Pushover); admin-wide targets receive admin alerts; private/LAN destinations blocked for members, allowed for admin targets; admin toggle "Let members use local addresses" default off.
- **Q3 2FA methods:** TOTP (QR) + 10 recovery codes (regenerable); passkeys as second factor AND passwordless sign-in; no email OTP.
- **Q4 2FA policy:** admin requires 2FA for `off|admins|everyone`, 7-day grace; admin resets a user's 2FA; magic link requires second factor when enabled; SSO logins skip local 2FA.
- **Q5 SSO accounts:** honor `auto_create_users`; optional allowed email domains; optional required group; every login syncs name, email, avatar, role, subgroups; SSO-sourced subgroup memberships removed when group dropped, manual ones untouched; username from `preferred_username`.
- **Q6 Providers:** presets Authentik (primary test target), Keycloak, Authelia, Google, Microsoft, GitHub, GitLab, Discord, Custom (any OIDC/OAuth2); GitHub/Discord fetch verified email from provider API; group→role/subgroup mapping editor with test-login preview; merge duplicate admin modules; delete dead `OIDCService`; no LDAP/SCIM.
- **Q7 PWA:** install banner + iOS "Add to Home Screen" steps; top safe-area; apple-touch-icon; shortcuts New post / Chat / Calendar; "New version — Reload" prompt; fix full-reload links; offline = last-viewed pages read-only, no offline writes.
- **Q8 Notifications:** per-device push list (rename/remove); real titles/bodies from registry text; `tag` per thread so they stack; click opens exact page in-app; app-icon unread badge; foreground OS notification when tab hidden only on devices without push.
- **Q11 Sign-in log:** every attempt (success/fail, method, IP, user agent → browser/OS); no geo lookup; user "Your devices" + "Sign out everywhere else"; admin searchable log + CSV, 90-day retention; new-device alert to user; admin alert when one IP fails ≥10 times in 10 min (via email + admin Apprise).
- **Q12 System page:** green/amber/red for DB, Valkey, Celery workers + queue depth, beat last run, last email success, push (VAPID) configured; disk used/free for media + DB, largest tables; version, migration head, uptime, container CPU/mem; 30 s refresh; alerts on disk > 85 %, worker down, email failing; link to Grafana when `GRAFANA_URL` set.
- **Q13 Audit:** log all security/admin changes (2FA, passkeys, SSO, SMTP, Apprise, SSO role sync, data export, admin 2FA reset); search/filters/CSV; no delete endpoint; 1-year retention; no hash chain.
- **Q15 NSFW:** label **"NSFW"** (not "Adults only"); toggle on posts, photo uploads, albums; hidden from non-adults everywhere (feed, groups, profiles, search, newsletter, notifications, On this day) incl. comments + media; adults see blur cover "NSFW — tap to view" or setting "Always show NSFW"; moderators flag/unflag; feature flag `nsfw` (default on).
- **Q16 Age groups:** `child` (<13), `teen` (13–17), `adult` (18+); admin-set wins, else from birthday, else not-adult; only restriction now = no NSFW for child/teen; Users tab edit; invites can preset.
- **Q17:** admin setting "Adult status needs admin approval" (default off; when on, birthday alone never makes adult); members suggest an age group with note → admin queue → approve applies + audit; subject not notified; user sees own group read-only.
- **Q18 Onboarding:** after first sign-in (any method): 1 photo/name/pronouns, 2 birthday (year hidden default), 3 contact + location (private default), 4 family relations + household/pets, 5 push on this device + digest, 6 2FA (required if policy demands). Admin picks required steps; progress saved; SSO pre-fills; existing users get a one-time "Complete your profile" card; tour runs after.
- **Plugins (2026-11-23, user: "Include the plugin system and the sassbot plugin"):** spec = `docs/superpowers/specs/2026-11-23-plugin-system-design.md` (copied from feat/frontend-overhaul) + its P1 plan `docs/superpowers/plans/2026-11-23-plugin-core-p1.md`. New system **replaces** the old in-process plugin system (manifest.toml, HookRegistry, nxr_plugin keys, frontend plugin JS, example-recipe-box/trivia, cookiecutter) — spec supersedes it. Repos `JMO-Labs/nexara-sassybot` and `JMO-Labs/nexara-plugins` created **public** (user approved). Plans 09–12 written when PR 8 lands, from the spec.
- **Q20–Q23 Countdowns (2026-11-23):** title, target date (+optional time), optional emoji/cover; scope community|subgroup|private like posts; optional yearly repeat (restarts day after). Creating one posts a feed card "N days until X" with Follow; follow from card or `/app/countdowns/{id}`; creator auto-follows. Home fixed "Countdowns" strip of followed, soonest first, ≤6 + "See all". Followers notified 7 days, 1 day, day-of (notif type `countdown_reminder`, toggle in matrix); "Today!" celebration card; leaves Home 3 days after (yearly restarts). Creator edit/delete; followers unfollow. PR 8, before plugins.
- **Birthday countdown TZ (2026-11-23):** `birthday_in_days` uses viewer's `users.timezone` date, not server UTC (PR 1 Task 7).
- **Q9/Q14/Q19 Delivery:** order above; passkeys tested behind user's HTTPS reverse proxy.

## Migration numbers (fixed)

| Rev | PR.Task | down_revision |
|---|---|---|
| 0068_mail_signin | 1.2/1.4 | 0067_prompt_answer_recount |
| 0069_apprise_admin | 2.1 | 0068_mail_signin |
| 0070_twofactor | 3.1 | 0069_apprise_admin |
| 0071_sso_sync | 4.1 | 0070_twofactor |
| 0072_push_devices | 5.2 | 0071_sso_sync |
| 0073_monitoring | 6.1 | 0072_push_devices |
| 0074_onboarding_age | 7.1 | 0073_monitoring |
| 0075_countdowns | 8.1 | 0074_onboarding_age |

## Global Constraints

- Files ≤ 400 lines; Doxygen `@file/@brief` headers; routes → services → repos (no repo imports in routes).
- Every query scoped by `community_id`; errors via `AppError` envelope.
- Frontend API paths start with `/api/v1/` (client adds no prefix); hook modules need `"use client"`.
- WCAG 2.1 AA; every icon button has `aria-label` (IconButton shows it as tooltip).
- Secrets never returned by API (return `has_password: bool` style flags); never logged.
- Conventional commits ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push to `github` remote only.
- Before each commit: `ruff check . && ruff format --check . && mypy app/`, `npx eslint . && npx prettier --check . && npx tsc --noEmit`, touched tests; before PR: full suites + `npx next build`.

## Review Focus

- Login with 2FA + passkey + magic link + SSO in every combination — no path issues tokens without the required second factor (tests in 3.3).
- SSO re-login after a user is removed from the required group / domain → login refused, existing sessions revoked (test in 4.2).
- NSFW post reached by direct URL, comment notification, search, share, or On this day by a teen → 404/absent (test in 7.3).
- Gmail app password with spaces pasted (`abcd efgh ijkl mnop`) → spaces stripped, works (test in 1.2).
- Apprise URL whose hostname resolves to 127.0.0.1/10.x/169.254.x (DNS rebinding style `json://myhost.local`) for a member → rejected at save and at send (test in 2.2).
