# PR 11 — Sassybot as a plugin

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Sassybot ships as the first official plugin (public repo `JMO-Labs/nexara-sassybot`, Node), strictly opt-in; the in-core Sassybot is removed and existing community settings carry over.
**Spec:** `docs/superpowers/specs/2026-11-23-plugin-system-design.md` §9, §10 P3. **Branch (core):** `feat/plat-11-sassybot` from `feat/plat-10-host`. **Plugin repo:** `/home/user/code/nexara-sassybot`, branch `main`. Task 1 → (2 ∥ 3 ∥ 5) → 4 → 6 → 7.

**Repo creation (approved by user):** `gh repo create JMO-Labs/nexara-sassybot --public --license mit --description "Sassybot: opt-in roast bot plugin for Nexara"` then `gh repo edit JMO-Labs/nexara-sassybot --add-topic nexara-plugin`.

**Rulings:**
- TypeScript, esbuild bundle → `dist/index.js` (spec entrypoint); runtime deps only `@anthropic-ai/claude-code` (pinned) + `@anthropic-ai/sdk` — fewer installs on host.
- State in `node:sqlite` (Node ≥22.13, matches host image) — `better-sqlite3` needs install scripts, host runs `--ignore-scripts` — cost: experimental-API warning.
- CI asserts `node node_modules/@anthropic-ai/claude-code/cli.js --version` works after `npm ci --omit=dev --ignore-scripts`; CLI `HOME`/`CLAUDE_CONFIG_DIR` = `$NEXARA_DATA_DIR/claude-home` (rootfs read-only) — cost if CLI needs postinstall: `claude-cli` provider unusable, owner uses `anthropic-api` (blocking flag to user).
- Mention or reply-to-bot from an author with `roast_level=off` → canned "Opt in under Settings › Plugins › Sassybot and I'll roast you." (no model call) — anti-goal: never roast non-opted users.
- `roast_level` `full` ≡ `spicy`; order `mild < medium < spicy`; thread = root post, cap 2 is a constant (spec).
- Dedupe per entity id (core sends `post.created` and `mention` for one post).
- Composer flag label "Roast me" (spec's emoji dropped for screen readers).
- `min_core_version` = core `app.__version__` at release (spec example `1.4.0` exceeds current `0.1.0`).
- `anthropic-api` model id = constant picked at build from current Claude API docs; no model setting in v1.
- Data migration: community settings → `plugin_seeds`, applied on first enable; community enablement NOT migrated (admin installs + enables = opt-in); `user_settings.allow_sassybot` NOT migrated (old opt-out default true → everyone starts `off`); old bot account (env `SASSYBOT_USER_ID`) reused so old comments keep their author.
- AI tab keeps provider/OCR/suggestions/budget; drops Sassybot section and `sassybot` budget feature; historic usage rows kept.

---

### Task 1: Plugin repo scaffold + release pipeline

**Files (nexara-sassybot):**
- Create: `package.json` (`"type":"module"`, `engines.node ">=22.13"`, scripts `build` (esbuild, external `@anthropic-ai/claude-code`), `test` (vitest), `lint` (tsc --noEmit + eslint + prettier)), `tsconfig.json`, `nexara-plugin.toml`, `assets/{icon,avatar}.png` (256 px), `README.md` (install + opt-in + subscription risk note §9), `.github/workflows/ci.yml`, `.github/workflows/release.yml`
**Interfaces:**
- Manifest: `id "io.jmolabs.sassybot"`, `runtime "node"`, `entrypoint "dist/index.js"`, `[bot] username "sassybot"`, scopes `posts:read comments:read comments:write media:read users:read`, events `post.created comment.created mention`, egress `api.anthropic.com claude.ai`.
- `[settings.*]`: `enabled` boolean true; `max_sass` select mild|medium|spicy default medium; `chance` number 0–1 default 0.15; `user_cooldown_hours` number 0–168 default 6; `daily_cap` number 0–500 default 30; `per_user_invoke_cap` number 0–50 default 3; `provider` select claude-cli|anthropic-api default claude-cli; `claude_token` secret; `anthropic_api_key` secret. `[user_prefs.roast_level]` select off|mild|full default off. `[composer_flags.roast_me]` boolean "Roast me".
- release.yml on tag `v*`: assert manifest `version` == tag; `npm ci && npm run build`; tar `nexara-plugin.toml dist package.json package-lock.json assets` → `io.jmolabs.sassybot-X.Y.Z.tar.gz` + `.sha256` (`sha256sum`); `gh release create`.
- [ ] Tests: `test/manifest.test.ts` parses TOML and matches `package.json` version; CI runs the claude-CLI-after-ignore-scripts check.
- [ ] Commit `chore: scaffold sassybot plugin and release workflow`

### Task 2: Webhook server, Nexara client, state

**Files:** Create `src/{index,server,verify,nexara,state,config}.ts`, `test/{verify,server,state}.test.ts`
**Interfaces:**
- `verify(secret, ts, body, sig, now) -> boolean` — `sha256=` HMAC of `` `${ts}.${body}` ``, reject `|now−ts| > 300`, `timingSafeEqual`.
- `node:http` server on `127.0.0.1:$PORT`, `POST /events` → 401 bad signature, 202 accepted then async handle; community from payload `community_id` → `NEXARA_COMMUNITIES` entry (`token`, `webhook_secret`, `settings`, `bot_user_id`).
- `class NexaraClient(url, token)`: `getPost(id)`, `listAuthorPosts(authorId, 20)` (`GET /api/v1/posts?author_id=`), `listComments(postId)`, `downloadMedia(id, dir) -> path`, `comment(postId, content, parentId?)`.
- `State($NEXARA_DATA_DIR/state.db)` tables: `daily(day, community, count)`, `invokes(day, community, user, count)`, `cooldown(community, user, at)`, `threads(post, replies)`, `pause(until)`, `handled(entity, at)` (prune > 7 days).
- [ ] Tests: spec vector signature ok / tampered / 301 s old; unknown community → 202 + ignored; duplicate entity handled once; day rollover resets counters.
- [ ] Commit `feat: webhook server, Nexara client and state store`

### Task 3: Decision engine (pure)

**Files:** Create `src/decide.ts`, `test/decide.test.ts`
**Interfaces:** `decide(ev, st, s, botUserId, now, rand) -> {action: 'reply'|'canned_invite'|'canned_off_clock'|'skip', sass?: 'mild'|'medium'|'spicy', reason}`. Order: `!s.enabled` / paused / handled → skip; `trigger` = `roast_me` (flags) | `mention` (event `mention` or `comment.parent_author_id == botUserId`) | `organic`; opted = `roast_level != off` or roast_me; mention && !opted → `canned_invite`; organic && !opted → skip; `daily(c) >= daily_cap` → skip; (roast_me|mention) && `invokes(u) >= per_user_invoke_cap` → `canned_off_clock`; thread replies ≥ 2 → skip; organic: `rand >= chance` or cooldown < `user_cooldown_hours` → skip; `sass = min(max_sass, level)` with `off+roast_me → mild`, `full → spicy`.
- [ ] Tests: roast_level off organic → skip; off + roast_me → reply mild; full + max medium → medium; roast_me ignores chance + cooldown; 4th invoke → off-clock; 31st reply → skip; 3rd thread reply → skip; mention from non-opted → invite; disabled kill switch beats everything.
- [ ] Commit `feat: sassybot decision engine with caps and opt-in`

### Task 4: Providers, prompt, queue

**Files:** Create `src/{prompt,queue,handle}.ts`, `src/providers/{claudeCli,anthropicApi,index}.ts`, `test/{prompt,providers,handle}.test.ts`
**Interfaces:**
- `systemPrompt(sass) -> string` — §9 voice rules verbatim lists (allowed / never), 1–2 sentences, `spicy` allows tasteful profanity, else output `PASS`.
- `claudeCli.run({prompt, system, images, token}) -> {text} | {rateLimited, resetAt?}` — `execFile(node, [cli.js, '-p', '--output-format', 'json', '--max-turns', '2', '--allowedTools', 'Read', '--append-system-prompt', system])`, env `CLAUDE_CODE_OAUTH_TOKEN`, 120 s timeout; images saved to tmp dir under `$NEXARA_DATA_DIR/tmp`, deleted after.
- `anthropicApi.run(...)` — `@anthropic-ai/sdk` messages with base64 images.
- Queue concurrency 1; rate limit → `pause(resetAt ?? now+1h)`; `PASS`/empty → no comment, nothing counted; success → comment + increment daily/invokes/cooldown/thread.
- Context: post/comment text, images, author display name, last 20 author posts, thread so far.
- [ ] Tests: `PASS` posts nothing; rate-limit pauses 1 h; two events processed sequentially (spy); token never in logs; prompt contains every "Never" item.
- [ ] Commit `feat: claude-cli and anthropic-api providers with serial queue`

### Task 5: Core prerequisites

**Files (nexara):** Modify `backend/app/api/v1/posts.py` + `services/post_service.py` + `repositories/post_repo.py` (`GET /api/v1/posts?author_id=` filter, same visibility rules); Test `backend/tests/integration/api/test_posts_author_filter.py`
- [ ] Tests: author filter returns only that author's posts the viewer may see; bot token with `posts:read` allowed.
- [ ] Commit `feat(posts): filter feed by author`

### Task 6: Remove core Sassybot + data migration

**Files (nexara):**
- Delete: `backend/app/services/ai/{sassybot_service,sassybot_runner}.py`, `backend/app/repositories/sassybot_repo.py`, `backend/tests/unit/services/ai/{test_sassybot,test_sassybot_runner,test_sassybot_trigger}.py`, `backend/tests/unit/tasks/test_ai_tasks_sassybot.py`, `backend/tests/integration/repositories/test_sassybot_repo.py`, `backend/tests/unit/repositories/test_sassybot_repo_count.py`
- Create: `backend/alembic/versions/0077_sassybot_extract.py` (down `0076_plugins`), `backend/app/models/plugin_seed.py`, `backend/tests/unit/migrations/test_sassybot_extract.py`
- Modify backend: `tasks/ai_tasks.py` (drop `_sassybot_async`, `sassybot_comment_task`), `services/post_service_base.py` (`_enqueue_sassybot`, `wants_sassybot` import), `services/post_service.py:199`, `services/post_comments.py:98`, `core/config.py` (`SASSYBOT_USER_ID`), `models/{community,user,user_settings}.py`, `schemas/settings.py`, `repositories/community_repo.py` (`SASSYBOT_COLUMNS`, `update_sassybot`), `repositories/settings_repo.py` (`count_sassybot_opt_outs`), `services/ai/{admin_ai_service,budget_service}.py`, `api/v1/admin_ai.py`, `services/plugin_service.py` (apply seed), `repositories/plugin_repo.py` (`pop_seed`); tests `tests/unit/services/conftest.py` (`sassybot_delay`), `tests/unit/services/{test_post_service,test_post_service_coverage}.py`, `tests/integration/api/test_admin_ai.py`, `tests/integration/repositories/test_community_ai_config.py`, `tests/unit/repositories/{test_community_repo,test_settings_repo}.py`, `tests/unit/schemas/test_settings_privacy_schema.py`, `tests/unit/services/ai/test_admin_ai_service.py`
- Modify frontend: `components/admin/AIConfigTab.tsx` (drop `SassybotSection`; notice "Sassybot is now a plugin" → `/app/admin/plugins`), `hooks/useAdminAI.ts`, `lib/api/{adminAI,settings}.ts`, `components/settings/PrivacyTab.tsx` (drop `allow_sassybot`; panel "Birthday"); tests `tests/unit/admin/AIConfigTab.test.tsx`, `tests/unit/settings/{PrivacyTab,useSettings}.test.tsx`; docs `docs/docs/user/sassybot.md` (install from plugin, opt-in via Settings › Plugins)
**Interfaces:**
- `plugin_seeds(plugin_id text, community_id uuid fk cascade, settings jsonb not null, bot_user_id uuid null fk users on delete set null, created_at, pk(plugin_id, community_id))`.
- Upgrade per community: `{enabled: sassybot_enabled, max_sass: {1:'mild',2:'medium',3:'spicy'}[sassybot_sass_level], chance: 0 if sassybot_invoke_only else sassybot_probability/100}`; `bot_user_id` = `os.environ["SASSYBOT_USER_ID"]` if a user with that id exists in the community (set `is_bot=true, is_active=false`); drop `communities_sassybot_{sass,prob}_chk`, 4 community cols, `users.sassybot_opt_out`, `user_settings.allow_sassybot`. Downgrade re-adds with defaults and restores community values from seeds.
- First `set_community(enabled=True)` for a plugin with a seed: `validate_values(manifest.settings, seed ∩ manifest keys)` merged under explicit values; `bot_user_id` reused (reactivated, username kept); seed deleted.
- [ ] Tests: level 3 / prob 40 / invoke_only false → `{max_sass:'spicy', chance:0.4, enabled:true}`; invoke_only → chance 0; env bot id → seed + `is_bot`; downgrade restores; enable applies seed once and reuses old bot; `git grep -i sassybot backend/app frontend/components frontend/lib` → only the AI-tab notice.
- [ ] Commit `refactor(ai): move sassybot out of core into plugin seed`

### Task 7: Release + polish PR 11
- [ ] Plugin: `npm test` + lint green; tag `v1.0.0` → release assets present, sha256 matches.
- [ ] Core: full suites + `npx next build`; eval rebuild (localhost:8090); live: migrated eval DB has seed; install Sassybot by package URL (release asset) → enable → settings show migrated values; user A `roast_level=off` posts → no reply; "Roast me" post → reply; user B `mild` → organic replies obey `chance`; `@sassybot` from opted-out user → invite line; 4th invoke → off-clock; set daily_cap 1 → second skipped; phone screenshots (Settings › Plugins › Sassybot, composer toggle, bot comment with badge); PRs "Platform 11: Sassybot plugin" (core) + nexara-sassybot README links back.
