# PR 6 — Admin monitoring + audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Admins see system health, disk, sign-ins, and a complete audit trail; get alerted.
**Spec:** `00-overview.md` (Q11–Q13). **Branch:** `feat/plat-6-monitor` from `feat/plat-5-pwa`. Tasks 1 → (2 ∥ 3 ∥ 4) → 5.

---

### Task 1: Health collector

**Files:**
- Create: `backend/alembic/versions/0073_monitoring.py`, `backend/app/services/system_health.py`, `backend/app/api/v1/admin_system.py`, `backend/app/schemas/admin_system.py`, `backend/app/tasks/health_tasks.py`
- Modify: `backend/pyproject.toml` (`psutil>=6`), `backend/app/tasks/celery_app.py` (beat `health-check` every 5 min, `maintenance` queue; beat writes `beat:last_run` in Valkey each tick)
- Test: `backend/tests/unit/services/test_system_health.py`, `backend/tests/integration/api/test_admin_system.py`

**Interfaces:**
- Migration: `audit_logs` index `(community_id, created_at desc)`, `(action)`; `communities.audit_retention_days int default 365`.
- `async def collect(session, settings) -> SystemHealth` with `components: list[Component{name, status: 'ok'|'warn'|'down', detail}]` for: database (`select 1` latency; warn > 200 ms), valkey (ping), workers (`celery_app.control.inspect(timeout=1).ping()`; down if none), queues (Valkey `llen` per queue; warn > 100), beat (`beat:last_run` age; warn > 10 min), email (`smtp_last_ok_at`/`smtp_last_error`; warn if last error newer than last ok), push (VAPID set? else warn "Not set up").
- `disk`: `shutil.disk_usage(MEDIA_ROOT)` (or S3 → "External storage" no %), DB size `pg_database_size(current_database())`, top 10 tables `pg_total_relation_size`.
- `runtime`: version (`app.__version__`), alembic head (`select version_num from alembic_version`), uptime (process start), `psutil.cpu_percent(None)`, `psutil.virtual_memory()` + cgroup limit `/sys/fs/cgroup/memory.max` when present.
- `GET /api/v1/admin/system` (admin only), cached 10 s.
- `health_tasks.check()` → `admin_alert('disk_high')` when used > 85 %, `'worker_down'`, `'email_failing'` (last error newer than last ok and < 1 h old).
- [ ] Tests: valkey down → component `down`, endpoint still 200; disk 90 % (mock) → alert called once; non-admin → 403.
- [ ] Implement → PASS → commit `feat(admin): system health collector and alerts`

---

### Task 2: System page UI

**Files:**
- Create: `frontend/components/admin/system/{SystemTab,ComponentGrid,DiskPanel,RuntimePanel}.tsx`, `frontend/lib/api/adminSystem.ts`
- Modify: `frontend/components/admin/adminNav.ts` ("System" first)
- Test: `frontend/tests/unit/admin/system/SystemTab.test.tsx`
- Status uses icon + word (not color alone): ok `CheckCircle` "Healthy", warn `AlertTriangle` "Needs attention", down `XCircle` "Down". `refetchInterval: 30_000`. Disk as bar with "%" text. "Open Grafana" link when `GRAFANA_URL` present in response.
- [ ] Tests: down component renders "Down" text; refetch interval set; disk 86 % bar has `aria-valuenow=86`.
- [ ] Implement → PASS → commit `feat(admin): system page with health, disk, and runtime`

---

### Task 3: Sign-in log + devices UI

**Files:**
- Create: `backend/app/api/v1/admin_signins.py`, `backend/app/api/v1/sessions.py`, `frontend/components/admin/SigninsTab.tsx`, `frontend/components/settings/security/YourDevices.tsx`
- Test: `backend/tests/integration/api/test_signins_api.py`, frontend tests for both components

**Interfaces:**
- `GET /api/v1/admin/signins?q=&success=&method=&since=&cursor=` (q matches email/ip/device); `GET /api/v1/admin/signins.csv` (same filters, streaming, cap 50 000 rows).
- `GET /api/v1/sessions` → refresh-token families of current user `{family_id, device, ip, last_seen, current: bool}`; `DELETE /api/v1/sessions/{family_id}`; `POST /api/v1/sessions/revoke-others`.
- YourDevices lives in Settings › Security: "Sign out everywhere else" with confirm.
- [ ] Tests: CSV header `time,email,user,method,success,reason,ip,device`; revoke-others keeps current family; user can't revoke other user's family (404).
- [ ] Implement → PASS → commit `feat(security): sign-in log for admins and device list for members`

---

### Task 4: Audit coverage + UI upgrades

**Files:**
- Modify: every write site from PRs 1–5 not yet auditing (grep `audit` per new route — checklist: email settings, Google connect, Apprise targets + settings, 2FA enable/disable/regenerate, passkey add/remove, admin 2FA reset, security policy, SSO provider CRUD + role sync, data export start), `backend/app/api/v1/admin.py` audit list (+`q`, `actor_id`, `action_prefix`, `since`, `until`), `backend/app/services/retention_service.py` (audit purge by `audit_retention_days`), `frontend/components/admin/AuditLogTab.tsx` (search, filters, CSV)
- Create: `backend/tests/integration/api/test_audit_coverage.py`
- Confirm no DELETE route exists for audit logs (test asserts 405 on `DELETE /api/v1/admin/audit`).
- [ ] Tests: each checklist action produces exactly one audit row with actor + target; CSV export; retention removes rows older than 365 days only.
- [ ] Implement → PASS → commit `feat(audit): full security coverage, filters, CSV, retention`

---

### Task 5: Polish PR 6
- [ ] Full suites + build; live: stop eval worker → System page shows Workers "Down" within 30 s and admin ntfy target receives alert (disk threshold is unit-tested only); screenshots; PR "Platform 6: admin monitoring and audit".

---

### Carry-overs from PR 3 (2026-11-24)
- TRUSTED_PROXIES / client_ip already shipped in PR 3 — drop the nginx `set_real_ip_from` item.
- Burn the 2fa_pending token on successful `/2fa/login` or passkey step (today it stays retryable with a valid factor for 5 min).
- YourDevices + "Sign out everywhere else" is the mitigation for the PR 3 rulings: passkey add/remove without re-auth.
