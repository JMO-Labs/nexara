# PR 12 — Plugin marketplace

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Jellyfin-style plugin catalog: third parties list via manifest + topic + release, a public registry builds `index.json` with tiers, blocklist and GitHub-Discussion ratings; admins browse, install, update from Admin › Plugins › Marketplace and manage Sources.
**Spec:** `docs/superpowers/specs/2026-11-23-plugin-system-design.md` §8, §10 P4. **Branch (core):** `feat/plat-12-market` from `feat/plat-11-sassybot`. **Registry repo:** `/home/user/code/nexara-plugins`, branch `main`. Task 1 → 2 → (3 ∥ 4) → 5 → 6.

**Repo creation (approved by user):** `gh repo create JMO-Labs/nexara-plugins --public --license mit --description "Nexara plugin registry and index"`; enable Discussions + Pages (Actions source) via `gh repo edit --enable-discussions` / `gh api`; create Discussion category **Plugins** (announcement-style) by hand once — the API cannot create categories.

**Rulings:**
- No migration — `plugin_indexes`, `tier`, `source_index`, status `blocked` exist since `0076_plugins`.
- Index builder = Python 3.12 stdlib script (`urllib`, `tomllib`, GitHub REST + GraphQL with `GITHUB_TOKEN`) — spec §13 suggestion; manifest rules copied from `backend/app/plugins/manifest.py` (test pins both against the same fixtures).
- "First-registered repo wins" = id claims persisted in `ids.lock.json` (id → repo), committed by the workflow — repo creation date is spoofable by old repos — cost: workflow needs `contents: write`.
- Rating % = `up/(up+down)`, count = `up+down`, from THUMBS_UP/THUMBS_DOWN reactions on the discussion's opening post; shown with Lucide `ThumbsUp` + text (`94% (52)`), not emoji.
- Default source `https://jmo-labs.github.io/nexara-plugins/index.json` (config `PLUGIN_DEFAULT_INDEX_URL`), inserted into `plugin_indexes` on first list when the table is empty; admins may disable but not delete it.
- Index fetched with `safe_fetch` (public URLs only, ≤5 MB); cache in Valkey `plugins:index:{index_id}` (TTL 7 d) so a GitHub outage keeps the last catalog.
- Catalog dedupe: same `id` in several sources → default source wins, then sources by name; blocklist = union of all sources.
- Install from index re-verifies the tarball manifest equals the index manifest (scopes/events/egress) — index could lie.
- Blocked plugin: install `blocked`, host stop, tokens revoked, bot inactive, notif `plugin_blocked` (PREF_MAP → `notif_system_*`) to owner + `admin_alert('plugin_blocked')`; unblocking needs a manual reinstall.
- Install from `community` tier allowed (spec) behind an extra tick "Unreviewed — install at your own risk".

---

### Task 1: Registry repo + index builder

**Files (nexara-plugins):**
- Create: `verified.toml` (`repos = ["owner/name", …]`), `blocklist.toml` (`[[block]] plugin_id, versions = "*" | ["1.0.0"], reason`), `ids.lock.json`, `scripts/build_index.py`, `scripts/validate.py`, `tests/{test_validate,test_build_index}.py` + `tests/fixtures/`, `.github/workflows/build-index.yml`, `README.md` + `CONTRIBUTING.md` (3 listing steps §8.1, tiers, how to get verified, how ratings work)
**Interfaces:**
- `validate(manifest: dict, tag: str, assets: list[str]) -> list[str]` (errors): schema rules, `version == tag.lstrip('v')`, assets `<id>-X.Y.Z.tar.gz` + `.sha256` present.
- `tier(repo) -> 'official'|'verified'|'community'` — owner `JMO-Labs` / in `verified.toml` / else.
- `build(repos, verified, blocklist, lock) -> (index: dict, lock: dict)` — topic search `topic:nexara-plugin` → latest release → manifest at tag → validate (skip + log on error) → claim check → ensure discussion `"{name} ({id})"` in category Plugins → reactions + comment count + stars → index.
- `index.json`: `{schema: 1, generated_at, blocklist: [...], plugins: [{id, name, description, author, repo, tier, icon_url, rating: {up, down, reviews, url}, stars, versions: [{version, min_core_version, package_url, sha256, manifest, published_at}]}]}` (versions newest first, all valid releases).
- Workflow: `schedule: cron "0 * * * *"`, `push: main`, `workflow_dispatch`; permissions `contents: write, pages: write, id-token: write, discussions: write`; run tests → build → commit `ids.lock.json` if changed → `actions/upload-pages-artifact` + `actions/deploy-pages`.
- [ ] Tests: version ≠ tag rejected; missing `.sha256` rejected; second repo claiming taken id skipped; JMO-Labs → official; verified list → verified; rating math 49/3 → up 49 down 3; blocklisted id still in `blocklist` but versions untouched (Nexara enforces).
- [ ] Commit `feat: registry index builder with tiers, claims and ratings`

### Task 2: Catalog backend

**Files (nexara):**
- Create: `backend/app/plugins/catalog.py`, `backend/app/services/plugin_catalog_service.py`, `backend/app/tasks/plugin_index_tasks.py`
- Modify: `core/config.py` (`PLUGIN_DEFAULT_INDEX_URL`), `repositories/plugin_repo.py` (index CRUD), `services/plugin_service.py` (`source:'index'`, `update`), `api/v1/plugins.py`, `tasks/celery_app.py` (beat `plugin-index-refresh` every 6 h, `maintenance`), `services/notification_service.py` (`PREF_MAP["plugin_blocked"]`), notification registry text
- Test: `backend/tests/unit/plugins/test_catalog.py`, `backend/tests/unit/services/test_plugin_catalog_service.py`, `backend/tests/integration/api/test_plugin_catalog_api.py`
**Interfaces:**
- `parse_index(raw: bytes) -> PluginIndex` (`schema == 1` else `AppError("invalid_index")`); `is_blocked(plugin_id, version, blocklist) -> bool`.
- `refresh_indexes() -> None` (task): per enabled index fetch → cache → `last_fetched_at`/`last_error`; then `enforce_blocklist()`.
- `catalog(q: str | None, tier: str | None) -> list[CatalogItem{id, name, description, author, repo, tier, icon_url, rating, stars, latest_version, compatible: bool, installed_version, update_available: bool, source_index}]` — blocked removed; `compatible` via `is_compatible`.
- `install(IndexInstall{source:'index', index_url, plugin_id, version, approved_scopes})` — version from cache, not blocked, compatible; tarball manifest == index manifest else `AppError("index_manifest_mismatch")`; then PR 10 package path; stores `tier`, `source_index`.
- `update(plugin_id, version: str | None, approved: Approval | None)` — newest compatible if None; grown scopes/events/egress vs granted → `AppError("reapproval_required", 409, details={added_scopes, added_events, added_egress})`; else host `PUT` new version.
- Routes (instance owner): `GET /api/v1/plugins/catalog?q=&tier=`, `POST /api/v1/plugins/{plugin_id}/update`, `GET|POST /api/v1/plugins/indexes`, `DELETE /api/v1/plugins/indexes/{index_id}` (default → 422 `default_index`), `PATCH .../{index_id}` `{enabled}`, `POST .../{index_id}/refresh`. Audit `plugin.update`, `plugin.index.*`, `plugin.blocked`.
- [ ] Tests: schema 2 → error recorded in `last_error`, old cache kept; blocked version hidden + install 422 `plugin_blocked`; refresh with blocklist hit → status blocked, host stop called, tokens revoked, one notification; update with new scope → 409 details; same scopes → one-click; incompatible `min_core_version` → `compatible:false`, install 422; non-owner admin → 403; empty table → default source seeded.
- [ ] Implement → PASS → commit `feat(plugins): catalog, index sources, updates and blocklist`

### Task 3: Marketplace tab

**Files:**
- Create: `frontend/components/admin/plugins/{MarketplaceTab,PluginCard,PluginDetailSheet,InstallApprovalDialog,TierBadge,RatingBadge}.tsx`, `frontend/lib/api/pluginCatalog.ts`, `frontend/hooks/usePluginCatalog.ts`
- Modify: `frontend/app/app/admin/plugins/page.tsx` (tabs Marketplace | Installed | Sources, Marketplace default; `?tab=` deep link)
- Test: `frontend/tests/unit/admin/plugins/{MarketplaceTab,InstallApprovalDialog,RatingBadge}.test.tsx`
- Card: icon (alt = name), name, `TierBadge` (official/verified/community, text not colour-only), `RatingBadge` (`94% (52)` + "17 reviews", link "Read / write reviews" → discussion, `rel="noopener"`), stars, description; search + tier filter. Detail sheet: scopes in plain language (`posts:read` → "Can read posts", …, `notifications:send` → "Can send you notifications"), events, egress ("Talks to api.anthropic.com"), settings list, versions.
- Install dialog: one checkbox per scope + egress line; community tier adds warning + extra tick; Install disabled until all ticked.
- [ ] Tests: rating 49/3 → "94% (52)"; no ratings → "No ratings yet"; community warning shown only for community; install disabled until all ticked; keyboard: Tab reaches every checkbox, Esc closes.
- [ ] Implement → PASS → commit `feat(admin): plugin marketplace tab`

### Task 4: Sources tab + update UX

**Files:**
- Create: `frontend/components/admin/plugins/{SourcesTab,ReapprovalDialog}.tsx`
- Modify: `frontend/components/admin/plugins/{InstalledTab,PluginDetail}.tsx` ("Update to X" badge + button; blocked banner "Blocked by registry: {reason}")
- Test: `frontend/tests/unit/admin/plugins/{SourcesTab,ReapprovalDialog}.test.tsx`
- Sources: table name/url/enabled switch/last fetched (relative)/last error; add (name + URL), refresh, remove (IconButton aria-label "Remove {name}"; disabled for default with tooltip "Default source can only be disabled").
- [ ] Tests: 409 `reapproval_required` opens dialog listing only added items; confirm resends with approvals; default source remove disabled; error text shown.
- [ ] Implement → PASS → commit `feat(admin): plugin sources and guided updates`

### Task 5: List Sassybot in the registry
- [ ] Confirm `JMO-Labs/nexara-sassybot` has topic + v1.0.0 assets; run workflow → `index.json` lists `io.jmolabs.sassybot` tier `official` with a discussion URL; add `docs/docs/developer/plugins.md` section "Listing your plugin" linking the registry README.
- [ ] Commit `docs(plugins): how to list a plugin in the marketplace`

### Task 6: Polish PR 12
- [ ] Registry tests green, Pages URL serves `index.json`. Core full suites + `npx next build`; eval rebuild (localhost:8090); live: fresh eval → Marketplace shows Sassybot (official, rating) → install with approvals → running; publish `v1.0.1` with an added scope → update badge → re-approval dialog → updated; add test source with blocklist entry for echo → refresh → echo `blocked`, owner notified; phone screenshots (Marketplace grid, detail sheet, install dialog, Sources); PR "Platform 12: plugin marketplace".
