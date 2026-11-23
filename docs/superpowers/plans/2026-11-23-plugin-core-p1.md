# Plugin Core Contract (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an out-of-process plugin integrate with Nexara: admin installs it from a manifest URL, it gets a bot account + scoped token, receives signed webhooks for posts/comments/mentions, and its settings/user prefs/composer flags are rendered by Nexara.

**Architecture:** New backend package `app/plugins/` (manifest, scopes, signing, events) plus model/repo/service/router per the strict layering. Plugin tokens resolve to bot users inside `get_current_user`; a single route→scope allowlist enforces deny-by-default. Webhooks go out via a Celery task on a new `plugins` queue. Frontend renders manifest-declared fields generically.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Celery, httpx, stdlib `tomllib`/`hmac`/`secrets`; Next.js 16, TanStack Query, shadcn/ui, vitest.

**Spec:** `docs/superpowers/specs/2026-11-23-plugin-system-design.md` (§5, §6). Phases P2–P4 get their own plans.

## Global Constraints

- Files ≤ 400 lines; Doxygen comments (`@file`, `@brief`, `@param`, `@return`) on files/classes/public fns.
- Layering: `api/v1` → `services` → `repositories` → `models`. Routes never import repos.
- Every query filters on `community_id`. Errors only via `core/exceptions.py` envelope.
- `mypy app/` strict, `ruff check . && ruff format --check .`, `npx eslint . && npx prettier --check .` pass before every commit.
- Conventional Commits, ≤72-char subject, no emojis, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Migration `down_revision` = output of `alembic heads` at the time of writing it (currently `a78f91338679`). Single head (guard test exists).
- Token format `nxp_` + `secrets.token_urlsafe(32)`; store sha256 hex only.
- Signature header `X-Nexara-Signature: sha256=<hex HMAC-SHA256(secret, f"{timestamp}.{body}")>`; also `X-Nexara-Delivery`, `X-Nexara-Timestamp` (unix seconds).
- Webhook delivery: 5 retries, exponential backoff, 10 s timeout, queue `plugins`.
- Plugin rate limit 120/min keyed on token id.
- Scopes (exact strings): `posts:read`, `posts:write`, `comments:read`, `comments:write`, `reactions:write`, `media:read`, `users:read`, `notifications:send`.
- Events (exact strings): `post.created`, `comment.created`, `mention`.
- Field types: `boolean`, `select`, `number`, `string`, `secret` (secret only in `[settings.*]`).
- UI: WCAG 2.1 AA; every generated control labelled from manifest `label`, `help` as description.

## Review Focus

1. Plugin token on a route not in the allowlist → 403 envelope, never the handler (Task 4 test).
2. Token after disable/uninstall/revoke → 401 immediately, no cache (Task 4 test).
3. Private post, subgroup post without bot membership, or author who blocked the bot → zero deliveries (Task 6 test).
4. Content authored by any bot user → zero deliveries (no bot loops) (Task 6 test).
5. `secret` settings never appear in any API response, only `"set": true/false` (Task 5 test).

---

### Task 0: Branch setup

- [ ] **Step 1:** `git fetch && git worktree add ../nexara-plugins -b feat/plugin-core origin/dev` (another session owns `feat/frontend-overhaul`; do not touch it).
- [ ] **Step 2:** `git cherry-pick 6213f581 <this plan commit>` (spec + plan; find with `git log --oneline -3 feat/frontend-overhaul -- docs/superpowers`). Run `cd backend && uv sync && pytest tests/unit -q`; Expected: baseline pass count recorded in task report.

---

### Task 1: Manifest parsing and value validation

**Files:**
- Create: `backend/app/plugins/__init__.py`, `backend/app/plugins/manifest.py`
- Test: `backend/tests/unit/plugins/test_manifest.py` (+ `__init__.py`)

**Interfaces:**
- Produces:
  - `class FieldSpec(BaseModel)`: `type: Literal["boolean","select","number","string","secret"]`, `label: str`, `help: str | None`, `default: Any`, `options: list[str] | None`, `min: float | None`, `max: float | None`, `max_length: int | None`
  - `class PluginManifest(BaseModel)`: `id`, `name`, `version`, `description`, `author`, `license`, `homepage`, `min_core_version`, `runtime: Literal["node","python"]`, `entrypoint`, `bot_display_name`, `bot_username`, `scopes: list[str]`, `events: list[str]`, `egress: list[str]`, `settings: dict[str, FieldSpec]`, `user_prefs: dict[str, FieldSpec]`, `composer_flags: dict[str, FieldSpec]`
  - `parse_manifest(text: str) -> PluginManifest` — raises `AppError(code="invalid_manifest")`
  - `validate_values(fields: dict[str, FieldSpec], values: dict[str, Any]) -> dict[str, Any]` — raises `AppError(code="invalid_plugin_value")`
  - `with_defaults(fields: dict[str, FieldSpec], values: dict[str, Any]) -> dict[str, Any]`
  - `KNOWN_SCOPES: frozenset[str]`, `KNOWN_EVENTS: frozenset[str]`

- [ ] **Step 1: Write failing tests**
  - `test_parses_spec_example` — the full TOML from spec §5 parses; `m.id == "io.jmolabs.sassybot"`, `m.bot_username == "sassybot"`, `m.user_prefs["roast_level"].options == ["off","mild","full"]`.
  - `test_rejects_unknown_scope` — `scopes=["db:write"]` → `AppError` code `invalid_manifest`.
  - `test_rejects_unknown_event`, `test_rejects_secret_in_user_prefs`, `test_rejects_bad_id` (id must match `^[a-z0-9]+(\.[a-z0-9-]+)+$`), `test_rejects_bad_semver`.
  - `test_validate_values`: select not in options → error; number outside min/max → error; unknown key → error; bool given `"yes"` → error; valid dict returned unchanged.
  - `test_with_defaults_fills_missing` — `with_defaults(prefs, {}) == {"roast_level": "off"}`.
- [ ] **Step 2:** `pytest tests/unit/plugins/test_manifest.py -v` → FAIL (import error).
- [ ] **Step 3:** Implement in `manifest.py` with `tomllib.loads`; map `[plugin]`, `[bot]`, `[permissions]`, `[settings.*]`, `[user_prefs.*]`, `[composer_flags.*]` onto the model.
- [ ] **Step 4:** Tests PASS; ruff + mypy clean.
- [ ] **Step 5:** Commit `feat(plugins): add manifest parser and field validation`.

---

### Task 2: Models and migration

**Files:**
- Create: `backend/app/models/plugin.py`, `backend/alembic/versions/0068_plugin_core.py` (use next free ordinal; check `ls alembic/versions`)
- Modify: `backend/app/models/__init__.py` (export), `backend/app/models/post.py` (`Post.plugin_flags`), `backend/app/models/user.py` (remove `sassybot_opt_out`)
- Test: `backend/tests/unit/models/test_plugin_models.py`

**Interfaces:**
- Produces ORM classes:
  - `PluginInstall`: `id` UUID pk, `plugin_id` text unique, `version` text, `manifest` JSONB, `manifest_url` text, `endpoint_url` text, `status` text default `"running"` (`running|disabled|failed|blocked`), `granted_scopes` ARRAY(Text), `installed_at`, `updated_at`
  - `PluginCommunity`: pk (`install_id` FK cascade, `community_id` FK), `enabled` bool, `bot_user_id` FK users, `settings` JSONB default `{}` (secret values stored encrypted), `webhook_secret` text (encrypted)
  - `PluginToken`: `id` UUID pk, `install_id` FK cascade, `community_id`, `token_hash` text unique, `created_at`, `revoked_at` nullable
  - `PluginUserPref`: pk (`install_id` FK cascade, `user_id` FK), `community_id`, `values` JSONB
  - `Post.plugin_flags: Mapped[dict[str, Any]]` JSONB `server_default='{}'`, not null
- Note: `endpoint_url` is a P1 addition to the spec table — where webhooks go. P2 sets it to `{PLUGIN_HOST_URL}/plugins/{plugin_id}/events`.

- [ ] **Step 1:** Failing test: instantiate each model; assert table names `plugin_installs`, `plugin_communities`, `plugin_tokens`, `plugin_user_prefs`; `"sassybot_opt_out" not in User.__table__.c`; `"plugin_flags" in Post.__table__.c`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement models; write migration (create 4 tables, add `posts.plugin_flags`, drop `users.sassybot_opt_out`; downgrade reverses). `grep -rn sassybot_opt_out backend/ frontend/` and remove remaining references.
- [ ] **Step 4:** Test PASS; `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on dev Postgres succeeds; migration single-head guard test passes.
- [ ] **Step 5:** Commit `feat(plugins): add plugin tables and post plugin_flags`.

---

### Task 3: Repository

**Files:**
- Create: `backend/app/repositories/plugin_repo.py`
- Test: `backend/tests/integration/test_plugin_repo.py` (real Postgres, follow existing integration fixtures)

**Interfaces:**
- Produces `class PluginRepository(BaseRepository)` with:
  - `get_install(plugin_id: str) -> PluginInstall | None`, `list_installs() -> list[PluginInstall]`, `create_install(**fields) -> PluginInstall`, `delete_install(install_id: UUID) -> None`
  - `get_community(install_id, community_id) -> PluginCommunity | None`, `upsert_community(pc: PluginCommunity) -> PluginCommunity`
  - `list_enabled_for_event(community_id: UUID, event: str) -> list[tuple[PluginInstall, PluginCommunity]]` — install `status == "running"`, community `enabled`, `event` in `manifest->'events'`
  - `add_token(install_id, community_id, token_hash) -> PluginToken`, `revoke_tokens(install_id, community_id: UUID | None) -> None`
  - `resolve_token(token_hash: str) -> tuple[PluginToken, PluginInstall, PluginCommunity] | None` — not revoked, install running, community enabled
  - `get_user_pref(install_id, user_id) -> dict[str, Any]` (empty if none), `set_user_pref(install_id, user_id, community_id, values) -> None`
  - `soft_delete_bot_content(bot_user_id: UUID) -> int` — sets `deleted_at` on posts, comments; deletes reactions; returns rows affected

- [ ] **Step 1:** Failing tests: `test_resolve_token_rejects_revoked`, `test_resolve_token_rejects_disabled_community`, `test_list_enabled_for_event_filters_by_event`, `test_soft_delete_bot_content_hides_posts_and_comments`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat(plugins): add plugin repository`.

---

### Task 4: Plugin token auth and scope allowlist

**Files:**
- Create: `backend/app/plugins/scopes.py`, `backend/app/plugins/tokens.py`
- Modify: `backend/app/core/dependencies.py` (`get_current_user`), `backend/app/core/rate_limit.py` (key func)
- Test: `backend/tests/unit/plugins/test_tokens.py`, `backend/tests/unit/plugins/test_plugin_auth.py`

**Interfaces:**
- Produces:
  - `new_token() -> tuple[str, str]` (plaintext, sha256 hex), `hash_token(token: str) -> str`
  - `PLUGIN_ROUTE_SCOPES: dict[tuple[str, str], str]` — `(METHOD, route path template)` → scope. Initial entries: GET post list + post detail → `posts:read`; POST create post → `posts:write`; GET comments → `comments:read`; POST comment → `comments:write`; POST reaction toggle → `reactions:write`; GET media file/metadata → `media:read`; GET user by id/username → `users:read`. Implementer copies exact templates from `api/v1/{posts,media,users}.py` (`request.scope["route"].path`).
  - `required_scope(method: str, path_template: str) -> str | None`
  - `get_current_user`: bearer starting `nxp_` → `repo.resolve_token(hash)`; none → `AuthenticationError`; route not in allowlist or scope not in `install.granted_scopes` → `AuthorizationError(code="plugin_scope_denied")`; else set `request.state.plugin_install_id`, `request.state.plugin_token_id`, return bot `User`. JWT path unchanged.
  - Rate-limit key: `f"plugin:{token_id}"` when `request.state.plugin_token_id` set, 120/min.

- [ ] **Step 1: Failing tests** (`AsyncMock(spec=PluginRepository)` idiom):
  - `test_valid_token_returns_bot_user`
  - `test_revoked_token_401` (resolve returns None → `AuthenticationError`)
  - `test_route_not_in_allowlist_403` (Review Focus 1)
  - `test_scope_not_granted_403`
  - `test_jwt_path_unchanged` (existing token still works)
  - `test_hash_token_stable_and_token_prefix` (`startswith("nxp_")`, len hash == 64)
  - `test_rate_limit_key_uses_plugin_token_id` (key == `"plugin:<token_id>"` when state set, else existing key)
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** PASS + full `tests/unit/test_dependencies.py` still green.
- [ ] **Step 5:** Commit `feat(plugins): authenticate plugin tokens with scope allowlist`.

---

### Task 5: Plugin service (install, enable, settings, prefs, uninstall)

**Files:**
- Create: `backend/app/services/plugin_service.py`, `backend/app/schemas/plugin.py`
- Test: `backend/tests/unit/services/test_plugin_service.py`

**Interfaces:**
- Consumes: Task 1 (`parse_manifest`, `validate_values`, `with_defaults`), Task 3 repo, Task 4 `new_token`, `core/encryption.{encrypt_secret,decrypt_secret,derive_fernet_key}`, `core/http_safe.safe_fetch`, `UserRepository`.
- Produces `class PluginService(repo, user_repo, community_id, session, settings)`:
  - `install(manifest_url: str, endpoint_url: str, approved_scopes: list[str]) -> PluginInstallOut` — fetch manifest with `safe_fetch` (max 64 KB); `approved_scopes` must equal `set(manifest.scopes)` else `AppError("scopes_not_approved", details={"scopes": [...], "events": [...], "egress": [...]})` (nothing persisted; the admin UI uses this as its review step); duplicate `plugin_id` → `AppError("plugin_already_installed")`. `endpoint_url` is admin-entered and NOT SSRF-filtered (plugins live on private networks); validate `http(s)://` only.
  - `enable(plugin_id: str) -> PluginCredentials` — create bot `User(is_bot=True, role="member", password_hash=None, email=f"{bot_username}+{install.id}@plugins.invalid", username=bot_username, display_name=bot_display_name)` on first enable (username collision → append `-bot`, then `-bot2`…); reactivate (`is_active=True`) on re-enable; new token + `secrets.token_hex(32)` webhook secret. Returns `PluginCredentials(token, webhook_secret, community_id)` — only time plaintext is exposed.
  - `disable(plugin_id: str) -> None` — `enabled=False`, revoke tokens, bot `is_active=False`.
  - `uninstall(plugin_id: str, delete_content: bool) -> None` — disable in all communities, `soft_delete_bot_content` if `delete_content`, delete install (cascades). Bot user rows stay (inactive) so old content keeps an author.
  - `get_settings(plugin_id) -> dict[str, Any]` — non-secret values as-is; secret fields → `{"set": bool}` (Review Focus 5).
  - `update_settings(plugin_id, values: dict[str, Any]) -> dict[str, Any]` — validate; encrypt `secret` fields; empty string for a secret = keep existing.
  - `decrypted_settings(pc: PluginCommunity, manifest: PluginManifest) -> dict[str, Any]` (used by P2 host).
  - `get_user_prefs(plugin_id, user_id) -> dict[str, Any]` (with defaults), `set_user_prefs(plugin_id, user_id, values) -> dict[str, Any]`.
  - `list_installed() -> list[PluginInstallOut]`, `list_enabled_ui() -> list[PluginUiOut]` (for members: id, name, `user_prefs` and `composer_flags` field specs only).
- Schemas: `PluginInstallIn`, `PluginInstallOut` (id, plugin_id, name, version, status, scopes, events, egress, enabled, bot_user_id, settings_schema), `PluginCredentials`, `PluginUiOut`, `PluginValuesIn(values: dict[str, Any])`, `PluginUninstallIn(delete_content: bool = False)`.

- [ ] **Step 1: Failing tests:** `test_install_requires_all_scopes_approved`, `test_install_rejects_duplicate`, `test_enable_creates_bot_and_returns_credentials_once`, `test_reenable_reuses_bot_user`, `test_disable_revokes_and_deactivates_bot`, `test_uninstall_delete_content_calls_soft_delete`, `test_uninstall_keeps_content_by_default`, `test_get_settings_masks_secrets` (response contains `{"set": True}`, not the value), `test_update_settings_blank_secret_keeps_existing`, `test_user_prefs_default_off`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement (split into `plugin_service.py` + `plugin_settings.py` if > 400 lines). **Step 4:** PASS. **Step 5:** Commit `feat(plugins): add plugin service`.

---

### Task 6: Event dispatch and webhook delivery

**Files:**
- Create: `backend/app/plugins/signing.py`, `backend/app/plugins/events.py`, `backend/app/tasks/plugin_tasks.py`
- Modify: `backend/app/tasks/celery_app.py` (queue `plugins`, route `app.tasks.plugin_tasks.*`), `backend/app/services/post_service.py` (one call after each `_emit_scoped` in `create_post` and `add_comment`), `deploy/docker-compose.yml` + Helm worker args (add `plugins` to `-Q`)
- Test: `backend/tests/unit/plugins/test_signing.py`, `backend/tests/unit/plugins/test_events.py`, `backend/tests/unit/tasks/test_plugin_tasks.py`

**Interfaces:**
- Produces:
  - `sign(secret: str, timestamp: int, body: bytes) -> str` (returns `"sha256=<hex>"`), `verify(secret, timestamp, body, signature, now: int, max_age: int = 300) -> bool`
  - `async dispatch_plugin_event(session: AsyncSession, community_id: UUID, *, post: Post, comment: Comment | None, author: User) -> None` — decides event(s): `post.created` or `comment.created`, plus `mention` for each enabled plugin whose bot username is in `NotificationService.detect_mentions(content)`. For each `(install, pc)` from `list_enabled_for_event`:
    - skip if `author.is_bot` (Review Focus 4)
    - skip unless install has `posts:read` (posts) / `comments:read` (comments)
    - skip unless `pc.bot_user_id in await resolve_audience(session, community_id, visibility=post.visibility, subgroup_id=post.subgroup_id, author_id=post.author_id)` and post visibility != `private` (Review Focus 3)
    - skip if author has blocked the bot (use the block lookup `BaseRepository.apply_block_filter` relies on)
    - build payload per spec §6.4: `delivery_id`, `event`, `community_id`, `occurred_at`, `data.post` (id, content, visibility, subgroup_id, author_id, created_at, `media: [{id, mime, url}]`), `data.comment` (id, content, parent_id, `parent_author_id`, created_at) when comment, `data.author` (id, username, display_name), `data.author_prefs` = `with_defaults(manifest.user_prefs, repo.get_user_pref(...))`, `data.flags` = `post.plugin_flags.get(plugin_id, {})`
    - `deliver_plugin_event.delay(endpoint_url, encrypted_secret, body_json: str, delivery_id: str)`
  - Celery `deliver_plugin_event(endpoint_url, encrypted_secret, body, delivery_id)` — decrypt, sign with `int(time.time())`, `httpx.post(..., timeout=10)`, `autoretry_for=(httpx.HTTPError,)`, `retry_backoff=True`, `max_retries=5`; non-2xx raises to trigger retry; 4xx other than 408/429 does not retry.
  - `dispatch_plugin_event` failures are caught and logged; never raise into `post_service`.

- [ ] **Step 1: Failing tests:**
  - signing: `test_sign_known_vector` (secret `"s"`, ts `1700000000`, body `b"{}"` → precomputed hex via `hmac.new`), `test_verify_rejects_old_timestamp` (now − ts = 301 → False), `test_verify_rejects_tampered_body`.
  - events: `test_post_created_enqueues_for_subscribed_plugin`, `test_bot_author_not_dispatched`, `test_private_post_not_dispatched`, `test_subgroup_post_without_bot_member_not_dispatched`, `test_blocked_author_not_dispatched`, `test_mention_event_when_bot_username_mentioned`, `test_payload_author_prefs_defaults_off`, `test_payload_includes_flags_slice`, `test_dispatch_error_swallowed` (repo raises → no exception).
  - task: `test_delivery_sends_signature_headers` (respx/httpx mock asserts 3 headers), `test_delivery_retries_on_500`, `test_delivery_no_retry_on_400`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS + `pytest tests/unit/services/test_post_service.py -q` still green.
- [ ] **Step 5:** Commit `feat(plugins): dispatch signed webhooks for post, comment, mention`.

---

### Task 7: API routes and post flags

**Files:**
- Create: `backend/app/api/v1/plugins.py`
- Modify: `backend/app/api/v1/router.py` (include), `backend/app/schemas/post.py` (`PostCreate.plugin_flags: dict[str, dict[str, Any]] = {}`), `backend/app/services/post_service.py` (validate flags against enabled plugins' `composer_flags` via `PluginService`, store on `Post.plugin_flags`; unknown plugin or field → `AppError("invalid_plugin_value")`), user schemas to expose `is_bot`; member list/picker repo queries add `User.is_bot.is_(False)`
- Test: `backend/tests/unit/api/test_plugins_api.py`, extend `backend/tests/unit/services/test_post_service.py`

**Interfaces:**
- Routes (prefix `/plugins`, errors via envelope):
  - Admin (`require_role("admin")`; install/uninstall additionally require the default community — compare `user.community_id` to configured default): `GET /plugins` → `list[PluginInstallOut]`; `POST /plugins` body `PluginInstallIn` → `PluginInstallOut`; `POST /plugins/{plugin_id}/enable` → `PluginCredentials`; `POST /plugins/{plugin_id}/disable` → 204; `DELETE /plugins/{plugin_id}` body `PluginUninstallIn` → 204; `GET|PUT /plugins/{plugin_id}/settings` → masked dict.
  - Member: `GET /plugins/ui` → `list[PluginUiOut]`; `GET|PUT /me/plugin-prefs/{plugin_id}` → dict.
- [ ] **Step 1: Failing tests:** `test_member_cannot_install_403`, `test_install_then_enable_returns_credentials`, `test_settings_get_masks_secret`, `test_prefs_roundtrip`, `test_create_post_with_valid_flag_stored`, `test_create_post_with_unknown_flag_rejected`, `test_bot_hidden_from_member_list`, `test_user_out_includes_is_bot`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS; full `pytest tests/unit -q` green; `mypy app/` clean.
- [ ] **Step 5:** Commit `feat(plugins): add plugin admin, prefs and post flag APIs`.

---

### Task 8: Frontend — admin Plugins tab and generic field form

**Files:**
- Create: `frontend/lib/api/plugins.ts`, `frontend/components/plugins/ManifestFieldsForm.tsx`, `frontend/components/admin/PluginsTab.tsx`, `frontend/components/admin/PluginInstallDialog.tsx`, `frontend/components/admin/PluginUninstallDialog.tsx`
- Modify: `frontend/components/admin/AdminTabs.tsx` (add "Plugins")
- Test: `frontend/tests/unit/plugins/ManifestFieldsForm.test.tsx`, `frontend/tests/unit/admin/PluginsTab.test.tsx`

**Interfaces:**
- Consumes Task 7 routes.
- Produces:
  - `plugins.ts`: types mirroring `PluginInstallOut`, `PluginCredentials`, `PluginUiOut`, `FieldSpec`; fns `listPlugins`, `installPlugin`, `enablePlugin`, `disablePlugin`, `uninstallPlugin(id, deleteContent)`, `getPluginSettings`, `putPluginSettings`, `listPluginUi`, `getMyPluginPrefs`, `putMyPluginPrefs`.
  - `<ManifestFieldsForm fields={Record<string, FieldSpec>} values={…} onSubmit={(v) => …} />` — boolean → Switch, select → Select, number → Input type=number with min/max, string → Input maxLength, secret → password Input with placeholder "Saved — leave blank to keep" when `{set:true}`; each control `<Label htmlFor>` + `aria-describedby` for `help`.
- Behaviour:
  - Install dialog: admin pastes manifest URL + endpoint URL and submits with `approved_scopes=[]`. Backend replies `scopes_not_approved` with `details.scopes/events/egress`; dialog shows them as plain-language checkboxes plus the egress hosts; submit re-enabled only when every scope is ticked, and resends with them.
  - Enable shows credentials once in a dialog with copy buttons and text "Copy these now. They will not be shown again."
  - Uninstall dialog: checkbox "Also delete all its posts and comments" (default unchecked).
- [ ] **Step 1: Failing tests:** form renders each field type with accessible label; secret shows saved placeholder; uninstall sends `deleteContent=false` by default and `true` when ticked; credentials dialog shows token once.
- [ ] **Step 2:** `npx vitest run tests/unit/plugins tests/unit/admin/PluginsTab.test.tsx` → FAIL. **Step 3:** Implement. **Step 4:** PASS; eslint + prettier + `npx tsc --noEmit` clean.
- [ ] **Step 5:** Commit `feat(frontend): add admin plugins tab and manifest field form`.

---

### Task 9: Frontend — user prefs, composer flags, bot badge

**Files:**
- Create: `frontend/components/settings/PluginsTab.tsx`, `frontend/components/feed/PluginComposerFlags.tsx`, `frontend/components/common/BotBadge.tsx` (or the folder holding author chips)
- Modify: `frontend/components/settings/SettingsTabs.tsx`, `frontend/components/feed/ComposerToolbar.tsx` or `PostComposer.tsx` (send `plugin_flags`), author chip component(s) to render `<BotBadge />` when `author.is_bot`
- Test: `frontend/tests/unit/settings/PluginsTab.test.tsx`, `frontend/tests/unit/feed/PluginComposerFlags.test.tsx`

**Interfaces:**
- Consumes `listPluginUi`, `getMyPluginPrefs`, `putMyPluginPrefs`, `ManifestFieldsForm`.
- `<PluginComposerFlags value onChange />` — renders one toggle per `composer_flags` field of each enabled plugin; value shape `{[pluginId]: {[flag]: value}}` → `PostCreate.plugin_flags`. Hidden entirely when no plugin declares flags.
- Settings "Plugins" tab hidden when `listPluginUi` returns no plugin with `user_prefs`.
- BotBadge: text "Bot" (and "Bot (inactive)" when `is_active === false` if exposed), meets contrast tokens.
- [ ] **Step 1: Failing tests:** settings tab saves prefs; composer flags included in submitted payload; flags hidden with no plugins; badge renders for `is_bot`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS; `npm test` full green; `npm run build` succeeds.
- [ ] **Step 5:** Commit `feat(frontend): plugin user prefs, composer flags and bot badge`.

---

### Task 10: Plugin developer contract doc + end-to-end smoke

**Files:**
- Create: `docs/plugins/contract.md`, `scripts/plugin-echo/echo.py` (≤60 lines, stdlib `http.server`: verifies signature with the same algorithm, prints payload, replies to `mention` by POSTing a comment with `NEXARA_TOKEN`)
- Test: manual smoke recorded in task report

- [ ] **Step 1:** Write `contract.md`: manifest reference (§5), scopes table, event list, payload JSON example, signature verification (Python + Node snippet, 5-min window), allowed routes (generated list of `PLUGIN_ROUTE_SCOPES`), rate limit, credential handling.
- [ ] **Step 2:** Smoke: run dev stack, host a manifest for `echo` (scopes `posts:read, comments:read, comments:write`, events all three), install via admin UI with `endpoint_url=http://host.docker.internal:8765/`, enable, run `echo.py` with credentials, create a post mentioning `@echo`. Expected: echo logs a verified `post.created` + `mention`, and a bot comment with a "Bot" badge appears in the thread; a private post produces no log line.
- [ ] **Step 3:** Commit `docs(plugins): add plugin contract and echo smoke plugin`.
- [ ] **Step 4:** Push branch, open PR to `dev` referencing the spec; CI green.
