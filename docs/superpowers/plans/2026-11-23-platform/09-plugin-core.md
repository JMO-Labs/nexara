# PR 9 — Plugin core contract

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Out-of-process plugins integrate safely: admin installs from a manifest URL, plugin gets a bot member + scoped token, receives signed webhooks, and its settings/prefs/composer flags render declaratively. Old in-process plugin system is deleted.
**Spec:** `docs/superpowers/specs/2026-11-23-plugin-system-design.md` §5, §6, §10 P1 (supersedes `2026-11-23-plugin-core-p1.md`; its task detail still applies where not overridden here). **Branch:** `feat/plat-9-plugins` from `feat/plat-8-countdowns`. Task 1 → 2 → 3 → (4 ∥ 5) → 6 → 7 → (8 ∥ 9) → 10 → 11.

**Rulings:**
- New package reuses `backend/app/plugins/` → old system deleted first (Task 1) — spec names that path — cost: none.
- 0076 drops old tables `plugins`, `plugin_data`, `plugin_api_keys` (only example-plugin data) — downgrade recreates them empty — cost: recipe-box/trivia rows lost (examples only).
- `users.sassybot_opt_out` drop moves to `0077_sassybot_extract` (PR 11) — core `sassybot_service.py:61` still reads it; keeps PR 9 shippable — cost: none.
- 0076 creates every §6.1 table incl. `plugin_indexes` + extra cols `manifest_url`, `endpoint_url`, `updated_at` → PRs 10/12 need no migration — cost: unused cols until then.
- One install route, body discriminated by `source`: `url` (P1: manifest URL + endpoint URL; plugin runs anywhere), `package` (PR 10), `index` (PR 12) — spec §10 "direct package URL" needs plugin-host, which is PR 10.
- In `url` mode the enable response returns credentials once (no host to hand them to) — cost: admin copies them manually.
- Instance owner = `admin` whose `community_id == settings.COMMUNITY_ID` → new dep `require_instance_owner`.
- Bots: mentionable (autocomplete keeps them) but hidden from directory/pickers/invites, skipped by onboarding (PR 7), 2FA policy (PR 3), age queue, digests and `NotificationService.notify`; never sent NSFW content (bots are not adult) — cost: plugin wanting NSFW must wait for a scope.
- `notifications:send` accepted in manifests but no allowlisted route in v1 (no plugin needs it) — documented in contract.md.
- Keep generic leftovers: notification category/`plugin_id` (future `notifications:send`), `interests.plugin_key`, widget category `plugin`.
- Core version for `min_core_version` = `app.__version__` (PR 6), compared with `packaging.version`.

---

### Task 1: Delete the old in-process plugin system

**Files:**
- Delete backend: `backend/app/plugins/` (all 10 files: `__init__,api_keys,context,hooks,loader,manifest,permissions,registry,task_loader,utils`), `backend/app/api/v1/{plugins,admin_plugins}.py`, `backend/app/models/plugin.py`, `backend/app/repositories/{plugin_repo,plugin_key_repo}.py`, `backend/app/schemas/plugin.py`, `backend/app/services/{plugin_service,plugin_lifecycle}.py`, `backend/app/tasks/plugin_tasks.py`
- Delete tests: `backend/tests/unit/plugins/`, `backend/tests/integration/plugins/`, `backend/tests/fixtures/plugins/`, `backend/tests/integration/api/{test_plugin_lifecycle,test_plugins}.py`, `backend/tests/integration/repositories/test_plugin_repos.py`, `backend/tests/integration/{test_plugin_migration,test_plugin_models_db}.py`, `backend/tests/unit/api/{test_admin_plugins,test_plugins_desc}.py`, `backend/tests/unit/core/test_plugin_key_dependency.py`, `backend/tests/unit/models/test_plugin.py`, `backend/tests/unit/repositories/test_plugin_key_repo.py`, `backend/tests/unit/schemas/test_plugin_schema.py`, `backend/tests/unit/services/{test_plugin_lifecycle,test_plugin_service,test_hooks_join_create}.py`, `backend/tests/unit/services/oauth/test_user_provisioner_hooks.py`, `backend/tests/unit/tasks/test_plugin_tasks.py`
- Delete repo root `plugins/` (contract_tests, contract_tester.py, example, example-recipe-box, example-trivia, cookiecutter-nexara-plugin); `docs/docs/developer/plugin-settings-phase4.md`
- Delete frontend: `frontend/plugins/`, `frontend/lib/plugins/{plugin-loader.ts,PluginSettingsContext.tsx}`, `frontend/lib/pluginPermissions.ts`, `frontend/components/admin/{PluginApiKeys,PluginDetail,PluginInstallDialog,PluginPermissionList,PluginSettingsForm,PluginsAdmin}.tsx`, `frontend/components/settings/PluginsSettingsTab.tsx`, `frontend/tests/unit/plugins/`, `frontend/tests/unit/admin/{PluginInstall,PluginSettings}.test.tsx`
- Modify: `backend/app/main.py` (`_load_plugins`, `HookRegistry.reset`), `backend/app/core/dependencies.py` (`get_plugin_from_api_key`), `backend/app/models/__init__.py`, `backend/app/api/v1/router.py`, `backend/app/tasks/celery_app.py` (`plugin_tasks` include/imports, `plugins.example_trivia.*` route, 2 trivia beat entries, `_load_plugin_tasks`), `HookRegistry.emit` call sites in `backend/app/services/{post_service,chat_service,community_service}.py`, `services/auth/registration.py`, `services/oauth/user_provisioner.py`; `backend/pyproject.toml` (`pythonpath ../plugins`, `broken-security` ruff ignore); `frontend/app/providers.tsx` (+`tests/unit/app/providers.test.tsx`), `frontend/components/settings/SettingsTabs.tsx` (provider + tab), `frontend/lib/query-keys.ts` (`pluginKeys`), `frontend/lib/api/plugins.ts` + `frontend/app/app/admin/plugins/{page,[id]/page}.tsx` (stub "Coming in this PR" until Task 8)
- [ ] Check: `git grep -n "HookRegistry\|nxr_plugin\|plugin-loader\|example_trivia\|recipe_box\|cookiecutter"` → empty; full backend unit + frontend suites green; mypy clean.
- [ ] Commit `refactor(plugins): remove in-process plugin system`

### Task 2: Manifest parser
**Files:** Create `backend/app/plugins/{__init__,manifest}.py`; Test `backend/tests/unit/plugins/test_manifest.py`
**Interfaces:** as old plan Task 1 (`FieldSpec`, `PluginManifest`, `parse_manifest`, `validate_values`, `with_defaults`, `KNOWN_SCOPES`, `KNOWN_EVENTS`) + `icon`, `bot_avatar`, `def core_version() -> str`, `def is_compatible(m) -> bool`. Id regex `^[a-z0-9]+(\.[a-z0-9-]+)+$`; version semver; scopes exactly `posts:read posts:write comments:read comments:write reactions:write media:read users:read notifications:send`; events `post.created comment.created mention`; `secret` only in `[settings.*]`.
- [ ] Tests: spec §5 TOML parses (`id io.jmolabs.sassybot`, `bot_username sassybot`, roast_level options); unknown scope/event, secret in user_prefs, bad id, bad semver → `invalid_manifest`; select not in options / number out of range / unknown key / `"yes"` for bool → `invalid_plugin_value`; `with_defaults(prefs, {}) == {"roast_level": "off"}`; `min_core_version` above core → incompatible.
- [ ] Commit `feat(plugins): manifest parser and field validation`

### Task 3: Models + migration
**Files:** Create `backend/app/models/plugin.py`, `backend/alembic/versions/0076_plugins.py` (down `0075_countdowns`); Modify `models/__init__.py`, `models/post.py`; Test `backend/tests/unit/models/test_plugin_models.py`, `backend/tests/unit/migrations/test_plugins_migration.py`
**Interfaces:**
- `plugin_installs(id uuid pk, plugin_id text unique, version text, manifest jsonb, manifest_url text null, endpoint_url text null, package_url text null, sha256 text null, source_index text null, tier text null check in ('official','verified','community'), status text default 'running' check in ('installing','running','disabled','failed','blocked'), granted_scopes text[] , installed_at, updated_at)`
- `plugin_communities(install_id fk cascade, community_id fk, enabled bool default false, bot_user_id fk users, settings jsonb default '{}', webhook_secret text /*Fernet*/, pk(install_id, community_id))`
- `plugin_tokens(id uuid pk, install_id fk cascade, community_id, token_hash text unique, created_at, revoked_at null)`
- `plugin_user_prefs(install_id fk cascade, user_id fk, community_id, values jsonb, pk(install_id, user_id))`
- `plugin_indexes(id uuid pk, url text unique, name text, enabled bool default true, last_fetched_at null, last_error text null)`
- `posts.plugin_flags jsonb not null server_default '{}'`; drop `plugins`, `plugin_data`, `plugin_api_keys`.
- [ ] Tests: table names; status check rejects `'weird'`; upgrade → downgrade → upgrade on real PG; `test_single_head.py` green.
- [ ] Commit `feat(plugins): plugin tables and post plugin_flags`

### Task 4: Repository
**Files:** Create `backend/app/repositories/plugin_repo.py`; Test `backend/tests/integration/repositories/test_plugin_repo.py`
**Interfaces:** old plan Task 3 signatures, `create_install(**fields)` takes all Task 3 columns; `list_enabled_for_event` requires status `running`.
- [ ] Tests: revoked token / disabled community / non-running install → `resolve_token` None; event filter; `soft_delete_bot_content` hides posts + comments, deletes reactions.
- [ ] Commit `feat(plugins): plugin repository`

### Task 5: Token auth, scopes, rate limit
**Files:** Create `backend/app/plugins/{scopes,tokens}.py`; Modify `backend/app/core/dependencies.py` (`get_current_user`, new `require_instance_owner`), `backend/app/core/rate_limit.py`; Test `backend/tests/unit/plugins/{test_tokens,test_plugin_auth}.py`
**Interfaces:** old plan Task 4: `new_token() -> tuple[str, str]` (`nxp_` + `secrets.token_urlsafe(32)`, sha256 hex), `hash_token`, `PLUGIN_ROUTE_SCOPES` keyed `(METHOD, template)`: `GET /api/v1/posts`, `GET /api/v1/posts/{post_id}` → `posts:read`; `POST /api/v1/posts` → `posts:write`; `GET /api/v1/posts/{post_id}/comments` → `comments:read`; `POST /api/v1/posts/{post_id}/comments` → `comments:write`; `POST /api/v1/posts/{post_id}/reactions`, `.../comments/{comment_id}/reactions` → `reactions:write`; `GET /api/v1/media/{media_id}`, `/file`, `/thumbnail` → `media:read`; `GET /api/v1/users/{user_id}`, `/lookup` → `users:read`. Rate key `plugin:{token_id}`, 120/min.
- [ ] Tests: valid token → bot user; revoked → 401; route not allowlisted → 403 `plugin_scope_denied`; scope not granted → 403; JWT path unchanged; key func; `require_instance_owner` rejects admin of a non-default community.
- [ ] Commit `feat(plugins): plugin token auth with scope allowlist`

### Task 6: Service + bot accounts
**Files:** Create `backend/app/services/{plugin_service,plugin_settings}.py`, `backend/app/schemas/plugin.py`; Modify bot exclusions: `repositories/user_repo.py` (`list_by_community*` add `User.is_bot.is_(False)`), login/magic-link/OAuth lookups in `services/auth/*` + `services/oauth/user_provisioner.py`, `notification_service.notify` (skip bots); Test `backend/tests/unit/services/test_plugin_service.py`
**Interfaces:** old plan Task 5 with: `install(body: PluginInstallIn)` where `PluginInstallIn = UrlInstall{source:'url', manifest_url, endpoint_url, approved_scopes} | PackageInstall | IndexInstall` (latter two raise `AppError("not_supported", 422)` until PRs 10/12); `set_community(plugin_id, community_id, enabled: bool | None, settings: dict | None) -> PluginCommunityOut` (+`credentials` on first enable in url mode). Bot `User(is_bot=True, role="member", password_hash=None, email=f"{username}+{install_id}@plugins.invalid")`; username collision → `-bot`, `-bot2`…; disable/uninstall → `is_active=False`, tokens revoked; re-enable reuses bot.
- [ ] Tests: install without all scopes → 422 `scopes_not_approved` with `details.scopes/events/egress`, nothing persisted; duplicate → `plugin_already_installed`; enable creates bot + returns creds once; re-enable reuses bot; disable revokes + deactivates; uninstall `delete_content` true/false; secrets masked `{"set": true}`; blank secret keeps old; prefs default `off`; bot absent from `list_by_community`; bot gets no notification.
- [ ] Commit `feat(plugins): plugin service and bot accounts`

### Task 7: Event dispatch + webhooks
**Files:** Create `backend/app/plugins/{signing,events}.py`, `backend/app/tasks/plugin_tasks.py`; Modify `backend/app/tasks/celery_app.py` (queue `plugins`, route `app.tasks.plugin_tasks.*`), `backend/app/services/post_service.py` (after `_emit_scoped` in create), `backend/app/services/post_comments.py` (after comment emit), `deploy/supervisord/conf.d/celery-worker.conf` + `deploy/helm/nexara/values.yaml` `worker.queues` (add `plugins`); Test `backend/tests/unit/plugins/{test_signing,test_events}.py`, `backend/tests/unit/tasks/test_plugin_tasks.py`
**Interfaces:** old plan Task 6 (`sign`, `verify(max_age=300)`, `dispatch_plugin_event`, `deliver_plugin_event` 5 retries / backoff / 10 s / no retry on 4xx except 408, 429). Audience via `services/realtime/audience.resolve_audience`; mentions via `services/mention_tags.py` parser; skip `post.is_nsfw`.
- [ ] Tests: known HMAC vector (secret `s`, ts `1700000000`, body `{}`); ts 301 s old rejected; private / subgroup-without-bot / blocked-author / bot-author / NSFW → 0 deliveries; `@echo` → `mention`; `author_prefs` defaults; flags slice; dispatch error swallowed; 3 headers sent; retry on 500, none on 400.
- [ ] Commit `feat(plugins): signed webhooks for post, comment, mention`

### Task 8: API + post flags
**Files:** Create `backend/app/api/v1/plugins.py`; Modify `router.py`, `schemas/post.py` (`plugin_flags: dict[str, dict[str, Any]] = {}`), `post_service.py` (validate flags vs enabled plugins' `composer_flags`), user schemas (`is_bot`); Test `backend/tests/integration/api/test_plugins_api.py`
**Interfaces:** owner: `GET /api/v1/plugins`, `POST /api/v1/plugins/install`, `DELETE /api/v1/plugins/{plugin_id}` body `{delete_content: bool=false}`; community admin: `PATCH /api/v1/plugins/{plugin_id}/communities/{community_id}`, `GET /api/v1/plugins/{plugin_id}/settings`; member: `GET /api/v1/plugins/ui`, `GET|PUT /api/v1/me/plugin-prefs/{plugin_id}`. Audit `plugin.install|uninstall|enable|disable|settings`.
- [ ] Tests: member install → 403; non-default-community admin install → 403; install→enable→creds; settings masked; prefs roundtrip; valid flag stored, unknown flag 422; `UserOut.is_bot`.
- [ ] Commit `feat(plugins): plugin admin, prefs and post flag APIs`

### Task 9: Admin UI (Installed)
**Files:** Rewrite `frontend/lib/api/plugins.ts`, `frontend/app/app/admin/plugins/{page,[id]/page}.tsx`; Create `frontend/components/plugins/ManifestFieldsForm.tsx`, `frontend/components/admin/plugins/{InstalledTab,PluginDetail,InstallUrlDialog,UninstallDialog,CredentialsDialog}.tsx`; Test `frontend/tests/unit/admin/plugins/*.test.tsx`, `frontend/tests/unit/plugins/ManifestFieldsForm.test.tsx`
- Page tabs: Installed now (Marketplace/Sources in PR 12). Detail: status, version, tier, scopes, events, egress, settings form, enable switch, uninstall. Field mapping + approval flow + "Copy these now. They will not be shown again." per old plan Task 8.
- [ ] Tests: each field type labelled + `aria-describedby` help; secret placeholder "Saved — leave blank to keep"; approval checkboxes gate submit; uninstall `delete_content` false by default.
- [ ] Commit `feat(admin): installed plugins and manifest field form`

### Task 10: Prefs, composer flags, Bot badge
**Files:** Create `frontend/components/settings/PluginPrefsTab.tsx`, `frontend/components/feed/PluginComposerFlags.tsx`, `frontend/components/ui/BotBadge.tsx`; Modify `SettingsTabs.tsx`, `feed/PostComposer.tsx` (send `plugin_flags`), `feed/PostHeader.tsx` + comment author line; Test `frontend/tests/unit/{settings/PluginPrefsTab,feed/PluginComposerFlags,ui/BotBadge}.test.tsx`
- [ ] Tests: prefs save; flags in payload; flags + tab hidden with no plugins; badge "Bot" / "Bot (inactive)".
- [ ] Commit `feat(plugins): user prefs, composer flags, bot badge`

### Task 11: Contract doc, echo smoke, polish PR 9
- Create `docs/docs/developer/plugins.md` (+ `docs/mkdocs.yml` nav) (manifest, scopes, events, payload, signature Python+Node, allowlisted routes, 120/min) and `scripts/plugin-echo/echo.py` (≤60 lines stdlib).
- [ ] Full suites + `npx next build`; eval rebuild (localhost:8090); live: install echo by URL, enable, `@echo` post → verified `post.created` + `mention`, bot comment with Bot badge; private post → no delivery; phone screenshots (Admin › Plugins, composer flag, Settings › Plugins); PR "Platform 9: plugin core contract".
