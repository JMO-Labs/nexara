# PR 10 — plugin-host sandbox

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** One-click install: Nexara hands a package URL to a separate `plugin-host` container that downloads, verifies, sandboxes (bubblewrap, per-plugin uid) and supervises plugin processes. No DB creds, no Docker socket.
**Spec:** `docs/superpowers/specs/2026-11-23-plugin-system-design.md` §7, §10 P2. **Branch:** `feat/plat-10-host` from `feat/plat-9-plugins`. Task 1 → 2 → (3 ∥ 4) → 5 → 6.

**Rulings:**
- No migration — `package_url`, `sha256`, `endpoint_url`, status `installing` already in `0076_plugins` — cost: none.
- Service lives at repo root `plugin-host/` (own `pyproject.toml`, uv), image `deploy/docker/plugin-host.Dockerfile` → `ghcr.io/jmo-labs/nexara-plugin-host`, port `8700` — spec §7.
- Nexara downloads the tarball first (`safe_fetch`, ≤50 MB), verifies sha256, reads `nexara-plugin.toml` from the tar (no extraction) for the approval step, then `PUT`s to the host — cost: double download.
- Host `PUT` returns 202 and installs async; Nexara sets `installing`, the 60 s poll flips to `running`/`failed` — npm/uv installs exceed request timeouts.
- Host keeps env (tokens, decrypted settings) in memory only; after a host restart it reports `needs_config` and the poll re-pushes `PUT` — cost: ≤60 s plugin downtime, no secrets on host disk.
- `NEXARA_COMMUNITIES` items also carry `bot_user_id` (Sassybot must recognise replies to itself; spec silent).
- bwrap needs user namespaces: compose/Helm run host with `cap_drop: [ALL]`, `cap_add: [SETUID, SETGID, CHOWN, KILL]`, `security_opt: [seccomp=unconfined, apparmor=unconfined]`, `no-new-privileges`, read-only rootfs + `/data` volume; startup self-test `bwrap --ro-bind / / true` → status `sandbox_unavailable`, no plugin starts — cost if wrong: unconfined seccomp widens kernel surface; upgrade path = custom seccomp profile.
- `url` install mode (PR 9) stays as "External plugin (advanced)" — dev + spec §10 "P3 can run against P1 alone".
- Unraid template deferred (compose + Helm only).

---

### Task 1: Host control API + installer

**Files:**
- Create: `plugin-host/pyproject.toml` (fastapi, uvicorn, httpx; dev pytest, respx), `plugin-host/host/{__init__,main,auth,installer,models}.py`, `plugin-host/tests/{test_auth,test_installer}.py`
**Interfaces:**
- Bearer `PLUGIN_HOST_SECRET` (`hmac.compare_digest`) on every control route; `/plugins/{id}/events` is unauthenticated at host (plugin verifies HMAC).
- `PUT /plugins/{id}` body `{version, package_url, sha256, runtime: 'node'|'python', entrypoint, env: {NEXARA_URL, NEXARA_TOKEN, NEXARA_WEBHOOK_SECRET, NEXARA_SETTINGS, NEXARA_COMMUNITIES}}` → 202; `DELETE /plugins/{id}` → 204 (stop, rm `/data/plugins/{id}`, keep `/data/plugin-state/{id}` unless `?purge=true`); `POST /plugins/{id}/start|stop`; `GET /plugins` → `[{id, version, status: installing|running|stopped|failed|needs_config|sandbox_unavailable, restarts, last_error}]`; `GET /plugins/{id}/logs?lines=200`.
- `async def install(spec) -> Path`: download (≤50 MB, https only) → sha256 mismatch → `failed:"sha256_mismatch"` → safe-extract (reject abs paths, `..`, symlinks, devices) to `/data/plugins/{id}/{version}/` → node `npm ci --omit=dev --ignore-scripts`; python `uv venv` + `uv pip install --only-binary :all: -r requirements.txt` → atomically swap `current` symlink → (re)start.
- [ ] Tests: missing/wrong bearer → 401; sha mismatch → failed, nothing extracted; tar with `../x` or symlink rejected; update swaps symlink and keeps previous version dir until success; manifest id ≠ path id → failed.
- [ ] Implement → PASS → commit `feat(plugin-host): control API and package installer`

### Task 2: Sandbox + supervisor + event proxy

**Files:**
- Create: `plugin-host/host/{sandbox,supervisor,proxy,logs}.py`, `plugin-host/tests/{test_sandbox,test_supervisor,test_proxy}.py`
**Interfaces:**
- `def bwrap_argv(plugin_id, uid, root: Path, state: Path, runtime, entrypoint) -> list[str]`: `--ro-bind / /`, `--tmpfs /tmp`, `--tmpfs /data` then `--ro-bind {root} /plugin`, `--bind {state} /state`, `--proc /proc`, `--dev /dev`, `--unshare-pid --unshare-ipc --die-with-parent --new-session`, `--chdir /plugin`; env `NEXARA_DATA_DIR=/state`, `PORT`, plus pushed env; no other plugins' dirs visible.
- uid = `20000 + stable index` stored in `/data/uids.json`; state dir chowned to it; spawn via `subprocess.Popen(user=uid, group=uid)`.
- Supervisor: restart with backoff 1,2,4,8,16 s; >5 crashes in 10 min → `failed`. Ports from 9100+.
- Proxy: `POST /plugins/{id}/events` → `http://127.0.0.1:{port}/events`, passes `X-Nexara-*` headers + body verbatim, 10 s timeout, 503 when not running.
- Logs: stdout/stderr lines → host stdout `[plugin_id] …` + ring buffer 200.
- [ ] Tests: argv never binds `/data/plugins` of another id; crash loop → `failed` after 6th crash in window; proxy preserves signature headers byte-for-byte; logs ring keeps last 200.
- [ ] Integration (marked `sandbox`, runs in image only): node plugin cannot read `/data/plugins/other`; can write `/state`.
- [ ] Implement → PASS → commit `feat(plugin-host): bubblewrap sandbox, supervisor, event proxy`

### Task 3: Image, compose, CI

**Files:**
- Create: `deploy/docker/plugin-host.Dockerfile` (python:3.12-slim + Node 22 LTS ≥22.13 + `bubblewrap` + uv; non-root files, `ENTRYPOINT uvicorn host.main:app --port 8700`), `.gitlab/ci/plugin-host.yml` (lint ruff/mypy + pytest in `plugin-host/`)
- Modify: `deploy/docker-compose.yml` (service `nexara-plugin-host`, volume `plugin_data:/data`, new network `nexara-plugins`; `nexara` joins `nexara-net` + `nexara-plugins`, host only `nexara-plugins`; caps/security_opt per Rulings; env `PLUGIN_HOST_SECRET`, `NEXARA_URL=http://nexara:8080`; nexara env `PLUGIN_HOST_URL=http://nexara-plugin-host:8700`, `PLUGIN_HOST_SECRET`), `deploy/docker-compose.dev.yml`, `deploy/.env.example` (`PLUGIN_HOST_SECRET=` + `openssl rand -hex 32` hint), `.gitlab/ci/build.yml` (second Kaniko job `DOCKERFILE_PATH=deploy/docker/plugin-host.Dockerfile`), `.gitlab/ci/container-scan.yml` (scan it), `.gitlab-ci.yml` include
- [ ] Check: `docker compose config` valid; `docker compose up` → `nexara-plugin-host` cannot resolve/reach `nexara-db:5432` (`nc -z` fails) but reaches `nexara:8080`; self-test passes on eval host.
- [ ] Commit `feat(deploy): plugin-host container in compose and CI`

### Task 4: Helm

**Files:**
- Create: `deploy/helm/nexara/templates/plugin-host.yaml` (Deployment replicas 1 + Service 8700 + PVC `/data`)
- Modify: `deploy/helm/nexara/values.yaml` (`pluginHost: {enabled: true, image: {repository: ghcr.io/jmo-labs/nexara-plugin-host, tag: ""}, persistence: {size: 2Gi}, resources, podSecurityContext}`), `templates/secrets.yaml` (`PLUGIN_HOST_SECRET`, generated if empty via `randAlphaNum 48` + lookup), `templates/config.yaml` (`PLUGIN_HOST_URL`), `templates/networkpolicy.yaml` (host ingress only from api+worker on 8700; host egress DNS + api:8080 + internet except `networkPolicy.privateCidrs`; api/worker egress += host:8700), `deploy/helm/nexara/README.md`
- [ ] Check: `helm lint` + `helm template` with `pluginHost.enabled=false` renders no host objects; NetworkPolicy denies host → postgres.
- [ ] Commit `feat(helm): plugin-host deployment and network policy`

### Task 5: Nexara ↔ host integration

**Files:**
- Create: `backend/app/services/plugin_host_client.py`, `backend/app/plugins/package.py`, `backend/app/tasks/plugin_host_tasks.py`
- Modify: `backend/app/core/config.py` (`PLUGIN_HOST_URL: str = ""`, `PLUGIN_HOST_SECRET: str = ""`), `services/plugin_service.py` (`source:'package'`; push env on enable/disable/settings change/uninstall), `api/v1/plugins.py` (`GET /api/v1/plugins/{plugin_id}/logs`), `tasks/celery_app.py` (beat `plugin-host-poll` every 60 s, `maintenance`), `frontend/components/admin/plugins/{InstallUrlDialog,PluginDetail}.tsx` (package URL + sha256 mode; logs panel `<pre>` with refresh; status badge text+icon)
- Test: `backend/tests/unit/services/test_plugin_host_client.py`, `backend/tests/unit/plugins/test_package.py`, `backend/tests/unit/tasks/test_plugin_host_tasks.py`, `frontend/tests/unit/admin/plugins/PluginLogs.test.tsx`
**Interfaces:**
- `class PluginHostClient(base_url, secret)`: `put(plugin_id, body) -> None`, `delete(plugin_id, purge: bool) -> None`, `start/stop(plugin_id)`, `status() -> list[HostPluginStatus]`, `logs(plugin_id, lines=200) -> list[str]`; host errors → `AppError("plugin_host_unavailable", 503)`.
- `async def fetch_package_manifest(url, sha256) -> PluginManifest` (raises `package_sha256_mismatch`, `invalid_manifest`).
- `endpoint_url = f"{PLUGIN_HOST_URL}/plugins/{plugin_id}/events"`; env `NEXARA_URL` = host-side value (not sent), `NEXARA_COMMUNITIES=[{community_id, token, webhook_secret, settings, bot_user_id}]`, `NEXARA_TOKEN`/`NEXARA_WEBHOOK_SECRET`/`NEXARA_SETTINGS` = default community's entry. New token per push; previous revoked.
- Poll: host `failed` → install `failed` + `admin_alert('plugin_failed')`; `needs_config` or missing → re-`PUT`; `running` → `running`.
- `PLUGIN_HOST_URL` empty → package mode returns `AppError("plugin_host_not_configured", 422)`; UI shows hint.
- [ ] Tests: sha mismatch nothing persisted; enable pushes env with decrypted secrets (never logged — caplog check); host down → install 503, status unchanged; poll re-pushes on `needs_config`; failed → alert once.
- [ ] Implement → PASS → commit `feat(plugins): install and supervise plugins via plugin-host`

### Task 6: Polish PR 10
- [ ] Full suites (+ `plugin-host` pytest) + `npx next build`; eval rebuild (localhost:8090) with host; live: install `plugin-echo` packaged as tarball (`scripts/plugin-echo/` + manifest) by package URL → `installing` → `running`; `@echo` mention answered; kill process 6× → `failed` + admin alert; restart host container → echo back within 60 s; `docker exec` host: echo uid cannot read another plugin dir; phone screenshots (install dialog, detail with logs); PR "Platform 10: plugin-host sandbox".
