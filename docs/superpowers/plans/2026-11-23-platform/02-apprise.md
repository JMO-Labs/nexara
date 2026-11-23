# PR 2 — Apprise

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Members and admins can actually use Apprise, safely.
**Spec:** `00-overview.md` (Q2). **Branch:** `feat/plat-2-apprise` from `feat/plat-1-mail`. Task 1 → 2 → 3.

---

### Task 1: SSRF guard + admin targets backend

**Files:**
- Create: `backend/alembic/versions/0069_apprise_admin.py`, `backend/app/services/notifications/apprise_guard.py`, `backend/app/services/admin_alerts.py`, `backend/app/api/v1/admin_apprise.py`
- Modify: `backend/app/services/apprise_service.py` (create/test call guard), `backend/app/tasks/notification_tasks.py` (send calls guard), `backend/app/models/apprise_url.py` (`user_id` nullable + `is_admin_target bool default false`), `backend/app/models/community.py` (`apprise_allow_local bool default false`)
- Test: `backend/tests/unit/services/notifications/test_apprise_guard.py`, `backend/tests/integration/api/test_admin_apprise.py`

**Interfaces:**
- `def check_apprise_url(url: str, *, allow_local: bool) -> None` raises `AppError("apprise_url_blocked", 422)`. Parse with `apprise.Apprise.instantiate(url)`; collect hosts from plugin attrs `host`; for each, `socket.getaddrinfo` → reject if any address `is_private|is_loopback|is_link_local|is_reserved|is_multicast` unless `allow_local`. Schemes without a host (e.g. `tgram://`, `discord://`, `pover://`) pass — they hit fixed public APIs.
- Members: `allow_local = community.apprise_allow_local`; admin targets: `allow_local=True`.
- `async def admin_alert(session, community_id, kind: str, data: dict) -> None` — sends to every active admin target + in-app `system` notification to admins; dedupe per `(kind, key)` 30 min in Valkey. Kinds: `signin_burst`, `disk_high`, `worker_down`, `email_failing`.
- API `GET/POST/DELETE /api/v1/admin/apprise/targets`, `POST .../{id}/test`, `PUT /api/v1/admin/apprise/settings {allow_local}`; audit `apprise.target.*`.
- Wire PR 1 burst stub to `admin_alert`.
- [ ] Tests: member `json://127.0.0.1/x` → 422; `json://10.0.0.5` → 422; member with `allow_local` on → OK; admin target `ntfy://192.168.1.10/topic` → OK; `tgram://bot/chat` → OK; send-time recheck blocks a URL whose host now resolves private (mock getaddrinfo); `admin_alert` twice in 30 min sends once.
- [ ] Implement → PASS → commit `feat(apprise): admin targets, alerts, and SSRF guard`

---

### Task 2: Member "Other apps" UI

**Files:**
- Modify: `frontend/lib/api/apprise.ts` (BASE `/api/v1/notifications/apprise`, field `apprise_url`, drop `service`), `frontend/components/settings/NotificationsTab.tsx`
- Create: `frontend/components/settings/AppriseSection.tsx`, `frontend/tests/unit/settings/AppriseSection.test.tsx`

**Interfaces:**
- Section title "Other apps"; list rows show label + masked scheme (`ntfy://…`), Test, Remove (IconButton aria-labels "Test {label}", "Remove {label}"); add form: Label, URL (`type="password"` toggle show), helper examples: `ntfy://ntfy.sh/your-topic`, `discord://webhook_id/webhook_token`, `tgram://bot_token/chat_id`, `pover://user@token`; link "All services" → `https://github.com/caronc/apprise/wiki`.
- Matrix Apprise column disabled with tooltip "Add an app first" when list empty.
- [ ] Tests: add calls POST with `{label, apprise_url}`; 422 `apprise_url_blocked` shows "That address is on a private network. Ask an admin to allow it."; empty list disables matrix column.
- [ ] Implement → PASS → commit `feat(settings): manage Apprise apps from notification settings`

---

### Task 3: Admin Apprise tab + polish
- Create `frontend/components/admin/AlertsTab.tsx` (targets list/add/test/remove + "Let members use local addresses" switch); nav entry "Alerts".
- [ ] Test: switch PUTs `{allow_local:true}`; target add uses admin endpoint.
- [ ] Polish: full suites + build, eval live (ntfy container `binwiederhier/ntfy` on eval network → admin target receives `admin_alert` test), screenshots, PR "Platform 2: Apprise".
