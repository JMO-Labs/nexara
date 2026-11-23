# Plugin System + Marketplace + Sassybot — Design

**Date:** 2026-11-23
**Status:** Draft — awaiting owner approval
**Supersedes:** `plans/components/12-plugin-system.md` (architecture, isolation, distribution sections) and the Sassybot section of `plans/components/19-plugin-ai-integration.md`.

---

## 1. Intent

Nexara needs an extension system that **community developers** can write plugins for and
that self-host admins can install **as easily as Jellyfin plugins** (browse a catalog, click
install) — but **safely**, because the code is written by strangers.

The first plugin is **Sassybot**: a funny, snappy bot member that roasts posts, comments and
pictures of people who opted in. It runs on the owner's Claude subscription via a long-lived
OAuth token (`claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`), the same pattern as the
as_work-q agent swarm (`claude -p` inside a worker).

## 2. Goals / Non-goals / Anti-goals

**Goals**
- Third-party plugins in any of Python or Node, installed from an admin marketplace, no restart.
- A plugin can only see and do what the admin approved at install.
- Plugins act through a bot member account, so their output uses the normal post/comment/notification/realtime paths.
- Third parties list a plugin with a manifest file + GitHub topic + GitHub Release. No form, no gatekeeper.
- Community ratings and reviews visible in the marketplace.
- Sassybot ships as the first official plugin and proves the contract.

**Non-goals (v1)**
- Plugin-supplied frontend JavaScript (no iframes, no bundles). UI is declarative only.
- Nexara starting/stopping Docker containers or k8s pods.
- Paid plugins, licensing, private catalogs with auth.
- Network egress enforcement per plugin (declared + displayed only; see §11).

**Anti-goals (failure even if it "works")**
- A plugin reads data the admin did not approve, or any data from the database directly.
- A slow, crashing or malicious plugin slows or breaks a core request.
- Sassybot roasts someone who did not opt in, or jokes about weight/bodies, health, grief, or kids.
- Sassybot drains the owner's subscription quota unchecked.

## 3. Approaches considered

| | Approach | Verdict |
|---|---|---|
| A | Plugins as **out-of-process apps**: signed webhooks in, scoped REST token out, bot account identity. One container per plugin, admin-managed. | Safe, but install is manual compose/helm edits. |
| **A′** | **A + shared `plugin-host` container** that downloads and runs plugin packages as sandboxed processes. Same contract as A. | **Chosen.** Jellyfin-style one-click install without giving Nexara the Docker socket. |
| B | In-process WASM sandbox (Extism). | Rejected: cannot spawn processes → no `claude` CLI; weak Python tooling. |
| C | Spec 12 as written (same-process Python, review-gated). | Rejected: zero isolation for untrusted code. |
| — | Nexara drives Docker socket / k8s API for true per-plugin containers. | Rejected for v1: root-equivalent on host if Nexara is compromised. |

Jellyfin (reference): in-process .NET DLLs, full trust, installed from JSON repository manifests.
We copy its **install UX** (repository URLs → catalog → click install), not its trust model.

## 4. Architecture

```
            GitHub                                   Self-hosted instance
┌──────────────────────────────┐        ┌──────────────────────────────────────────────┐
│ plugin repos (topic:         │        │ ┌───────────┐ signed webhooks ┌─────────────┐ │
│  nexara-plugin, Releases)    │        │ │ Nexara    │ ──────────────► │ plugin-host │ │
│            │ hourly Action   │ index  │ │ backend   │ ◄────────────── │  sassybot/  │ │
│            ▼                 │ .json  │ │ + celery  │  REST + scoped  │  giphy/ ... │ │
│ JMO-Labs/nexara-plugins ─────┼───────►│ └───────────┘  plugin token   └─────────────┘ │
│  index builder, verified,    │ (Pages)│   admin UI: Marketplace      no DB creds,     │
│  blocklist, Discussions      │        │                              no docker socket │
└──────────────────────────────┘        └──────────────────────────────────────────────┘
```

Three deliverables:
1. **Core plugin contract** in Nexara (backend + admin/user UI).
2. **`plugin-host`** service (new container in compose + Helm).
3. **Registry** repo `JMO-Labs/nexara-plugins` (index builder, tiers, ratings) + **Sassybot** repo.

## 5. Plugin manifest — `nexara-plugin.toml`

Lives at the plugin repo root and inside the release tarball.

```toml
[plugin]
id = "io.jmolabs.sassybot"        # reverse-DNS, globally unique
name = "Sassybot"
version = "1.0.0"                  # semver; must equal release tag (v1.0.0)
description = "A snappy bot that roasts people who ask for it."
author = "JMO Labs"
license = "MIT"
homepage = "https://github.com/JMO-Labs/nexara-sassybot"
min_core_version = "1.4.0"
runtime = "node"                   # "node" | "python"
entrypoint = "dist/index.js"       # node: file; python: "module:app"-style or script path
icon = "assets/icon.png"

[bot]                              # identity of the plugin's bot member
display_name = "Sassybot"
username = "sassybot"
avatar = "assets/avatar.png"

[permissions]                      # scopes; admin approves all at install
scopes = ["posts:read", "comments:read", "comments:write", "media:read", "users:read"]
events = ["post.created", "comment.created", "mention"]
egress = ["api.anthropic.com", "claude.ai"]   # declared, shown to admin (not enforced v1)

[settings.daily_cap]               # admin settings → auto form in Admin → Plugins → X
type = "number"
label = "Max replies per day (community)"
min = 0
max = 500
default = 30

[settings.claude_token]
type = "secret"
label = "Claude OAuth token"

[user_prefs.roast_level]           # per-user → Settings → Plugins → X
type = "select"
label = "Roast me"
options = ["off", "mild", "full"]
default = "off"

[composer_flags.roast_me]          # toggle in post composer
type = "boolean"
label = "🔥 Roast me"
```

Field types (shared by settings / user_prefs / composer_flags): `boolean`, `select`
(`options`), `number` (`min`, `max`), `string` (`max_length`), `secret` (settings only).
Every field has `label` and optional `help`, `default`. Nexara validates values server-side
against the manifest; plugins never get to render UI.

## 6. Core contract (Nexara backend)

New package `app/plugins/` following the strict layering (api → service → repo → model).

### 6.1 Data model (one migration; check `alembic heads` first)

| Table | Key columns |
|---|---|
| `plugin_installs` | `id`, `plugin_id` (manifest id), `version`, `manifest` JSONB, `package_url`, `sha256`, `source_index`, `tier`, `status` (`installing`/`running`/`disabled`/`failed`/`blocked`), `granted_scopes` TEXT[], `installed_at` |
| `plugin_communities` | `install_id`, `community_id`, `enabled`, `bot_user_id` → users, `settings` JSONB (secrets encrypted with `core/encryption.py`), `webhook_secret` (encrypted) |
| `plugin_tokens` | `id`, `install_id`, `community_id`, `token_hash` (sha256), `created_at`, `revoked_at` |
| `plugin_user_prefs` | `install_id`, `user_id`, `community_id`, `values` JSONB; PK (`install_id`, `user_id`) |
| `plugin_indexes` | `id`, `url`, `name`, `enabled`, `last_fetched_at`, `last_error` |
| `posts.plugin_flags` | new JSONB column, `{plugin_id: {flag: value}}`, default `{}` |

Install is **instance-wide** (one package on plugin-host); enablement, settings, bot account and
token are **per community** (multi-tenancy rule). Drop the unused `users.sassybot_opt_out`
column in the same migration; `users.is_bot` (exists, unused) becomes live.

### 6.2 Bot accounts
- On enable for a community: create `User(is_bot=True, role="member", password_hash=None, email=f"{username}+{install_id}@plugins.invalid")`, display name/avatar from manifest.
- Bot users cannot log in (no password, excluded from login/magic-link/OAuth lookups), are hidden from member pickers/invites, show a **Bot** badge in the UI.
- **Lifecycle (owner decision):** disable in a community or uninstall → bot `is_active=False`, token revoked, content kept, UI badge "Bot (inactive)"; re-enable reactivates the same bot user. Uninstall dialog offers an optional **"Also delete all its content"** checkbox → soft-deletes (`deleted_at`) the bot's posts/comments/reactions in all communities.
- Bot is a normal member for visibility: it sees community-visibility content; subgroup content only if an admin adds the bot to that subgroup. Private content never.

### 6.3 Auth + scopes
- Plugin token format: `nxp_<32 random bytes base62>`; stored as sha256 only; shown to plugin-host once at enable.
- `get_current_user` (core/dependencies.py): if bearer starts with `nxp_` → look up `plugin_tokens` (not revoked, install `running`, community enabled) → return bot user, stash scopes on `request.state.plugin_scopes`.
- New dependency `require_scope("comments:write")` on every route a plugin may call. Human JWTs pass; plugin tokens need the scope. Routes without `require_scope` reject plugin tokens (deny by default).
- v1 scopes: `posts:read`, `posts:write`, `comments:read`, `comments:write`, `reactions:write`, `media:read`, `users:read` (public profile fields only), `notifications:send`.
- Per-plugin rate limit via existing `slowapi` limiter, keyed on token id (default 120/min).

### 6.4 Event delivery (webhooks)
- Emit points: post created, comment created, mention of a bot username (in post or comment). One call `plugin_events.dispatch(community_id, event, entity)` at the same places the realtime `EventBus` is emitted for these (`FeedEvent.POST_CREATED`, `COMMENT_CREATED`).
- Dispatch enqueues a Celery task on new queue **`plugins`**; never awaits plugin I/O in the request.
- Task filters: plugin enabled in that community, subscribed to the event, has `*:read` scope for the entity, bot user can view the entity (reuse visibility/`_can_view` + block filter — authors who blocked the bot are skipped), author is not a bot (no bot-to-bot loops).
- Payload (JSON):
  ```json
  {"delivery_id":"uuid","event":"post.created","community_id":"…","occurred_at":"…",
   "data":{"post":{…public post fields, media:[{id,mime,url}]…},
           "author":{"id","username","display_name"},
           "author_prefs":{"roast_level":"mild"},
           "flags":{"roast_me":true}}}
  ```
  `author_prefs` = that plugin's `plugin_user_prefs` for the author, **merged over manifest defaults** (every declared pref always present; missing row → defaults, e.g. `roast_level: "off"`); `flags` = that plugin's slice of `posts.plugin_flags`. Media URLs require the token (`media:read`).
- POST to `{PLUGIN_HOST_URL}/plugins/{plugin_id}/events` with headers `X-Nexara-Delivery`, `X-Nexara-Timestamp`, `X-Nexara-Signature: sha256=HMAC(webhook_secret, timestamp + "." + body)`. Plugin must reject timestamps > 5 min old.
- Retries: 5 attempts, exponential backoff (Celery `autoretry_for`, `retry_backoff=True`), 10s timeout. Failures logged; no delivery table in v1.

### 6.5 Declarative UI (frontend)
- `Admin → Plugins`: tabs **Marketplace**, **Installed**, **Sources** (index URLs).
- Installed plugin page: status, version, tier, granted scopes, events, egress, auto-generated **settings form** from `[settings.*]` (shadcn form controls; `secret` = write-only), enable/disable per community, update button, uninstall.
- `Settings → Plugins` (every user): auto-generated form per enabled plugin from `[user_prefs.*]`.
- Post composer: one toggle/select per `[composer_flags.*]` of enabled plugins, saved to `posts.plugin_flags`.
- Bot badge on author chips for `is_bot` users.
- WCAG 2.1 AA: all generated controls labelled from manifest `label`/`help`, keyboard reachable.

### 6.6 Admin API (all `require_role("admin")`)
Instance-wide actions (install, update, uninstall, index sources) require `admin` in the default
community (the instance owner); per-community enable/settings require `admin` of that community.
`GET /plugins/catalog`, `POST /plugins/install {index_url, plugin_id, version, approved_scopes}`,
`POST /plugins/{id}/update`, `DELETE /plugins/{id}`, `PATCH /plugins/{id}/communities/{cid}` (enable/settings),
`GET|POST|DELETE /plugins/indexes`. User API: `GET|PUT /me/plugin-prefs/{plugin_id}`.
Errors via the standard `AppError` envelope.

## 7. plugin-host

New Python service `plugin-host/` at repo root (FastAPI + stdlib `subprocess`), image based on
python + Node LTS + `bubblewrap`. Added to `deploy/docker-compose.yml` and Helm.

- **Network:** on its own Docker network that reaches only the Nexara backend (via proxy) and the internet. No Postgres/Valkey access, no DB creds, no Docker socket.
- **Control API** (called only by Nexara, auth: shared `PLUGIN_HOST_SECRET` bearer):
  `PUT /plugins/{id}` (install/update: `package_url`, `sha256`, `runtime`, `entrypoint`, `env`),
  `DELETE /plugins/{id}`, `POST /plugins/{id}/start|stop`, `GET /plugins` (status).
- **Install:** download tarball → verify sha256 → extract to `/data/plugins/{id}/{version}/` →
  deps: node `npm ci --omit=dev --ignore-scripts`; python `uv venv` + `uv pip install -r requirements.txt` (no sdist builds: `--only-binary :all:`) → swap symlink `current` → restart process.
- **Run:** each plugin as its own Unix uid, under `bwrap` with read-only root, writable only
  `/data/plugin-state/{id}/` (exposed as `$NEXARA_DATA_DIR`), private `/tmp`, no other plugins' dirs visible.
  Env: `NEXARA_URL`, `NEXARA_TOKEN` (per community → see below), `NEXARA_WEBHOOK_SECRET`, `PORT`, `NEXARA_SETTINGS` (JSON incl. decrypted secrets).
  Plugin runs an HTTP server on `127.0.0.1:$PORT`; host reverse-proxies `/plugins/{id}/events` to it.
- **Multi-community:** v1 passes `NEXARA_COMMUNITIES` = JSON list of `{community_id, token, webhook_secret, settings}`; event payload carries `community_id`. (Single default community is the common case.)
- **Supervision:** restart on crash with backoff (max 5 in 10 min → status `failed`, reported to Nexara via `GET /plugins` poll every 60s by a Celery beat job).
- Logs: plugin stdout/stderr to host stdout prefixed `[plugin_id]`; last 200 lines via `GET /plugins/{id}/logs` shown in admin UI.

## 8. Registry + marketplace

### 8.1 Listing a plugin (third-party dev)
1. `nexara-plugin.toml` at repo root.
2. GitHub topic **`nexara-plugin`** on the repo.
3. GitHub Release tagged `vX.Y.Z` with assets `<id>-X.Y.Z.tar.gz` and `<id>-X.Y.Z.tar.gz.sha256`.

### 8.2 Registry repo `JMO-Labs/nexara-plugins`
- `verified.toml` — repo list reviewed by maintainers (added via PR).
- `blocklist.toml` — `{plugin_id, versions = "*" | [..], reason}`.
- `.github/workflows/build-index.yml` — hourly + on push:
  search repos by topic → read manifest at latest release tag → validate (schema, version == tag,
  sha256 asset present, id unique — first-registered repo wins) → compute tier
  (`official` = JMO-Labs org, `verified` = in verified.toml, else `community`) → ensure one
  GitHub Discussion per plugin in category "Plugins" (create if missing) → read its 👍/👎 counts +
  comment count + repo stars → write `index.json` → publish to GitHub Pages.
- `index.json` (default source URL baked into Nexara, admins may add others):
  ```json
  {"schema":1,"generated_at":"…","blocklist":[…],
   "plugins":[{"id","name","description","author","repo","tier","icon_url",
     "rating":{"up":49,"down":3,"reviews":17,"url":"<discussion url>"},"stars":120,
     "versions":[{"version","min_core_version","package_url","sha256","manifest":{…},"published_at"}]}]}
  ```

### 8.3 Ratings + reviews
- One GitHub Discussion per plugin; 👍/👎 on its opening post = rating, comments = reviews.
- Marketplace shows `94% 👍 (52)` + review count + "Read / write reviews" link to the discussion.
- Requires a GitHub account to rate (spam resistance, zero infra). In-app ratings: deferred.

### 8.4 In Nexara
- Celery beat job (every 6h, `maintenance` queue) fetches each enabled index URL, caches in Valkey.
- Marketplace card: icon, name, tier badge, rating, stars, description; detail sheet lists scopes, events, egress, settings, versions.
- Install dialog: lists every scope + egress in plain language ("Can read posts and comments", "Talks to api.anthropic.com"); `community` tier adds an "Unreviewed — install at your own risk" warning; admin must tick to approve.
- Updates: badge when a newer compatible version exists. If scopes/events/egress grew → re-approval dialog; otherwise one click.
- Blocklist hit on refresh → install set `blocked`, plugin stopped, token revoked, admins notified (new notif type → extend `PREF_MAP`).

## 9. Sassybot (first plugin, repo `JMO-Labs/nexara-sassybot`, tier official)

Node plugin; dependency `@anthropic-ai/claude-code` (the `claude` CLI).

**Who gets roasted** — only if `author_prefs.roast_level != "off"` **or** the post has `flags.roast_me`.
Effective sass = `min(admin max_sass, author roast_level)`; a roast-me post with prefs `off` uses `mild`.

**Triggers**
- `post.created` / `comment.created` on opted-in author: reply with probability `chance` (admin, default 0.15), skipped if that author was roasted within `user_cooldown_hours` (default 6).
- Roast-me post: always reply (skips chance + cooldown).
- `mention` (@sassybot) or a direct reply to a Sassybot comment: reply, max **2** Sassybot replies per thread, then silent.

**Hard caps (admin, enforced before every model call, all triggers count)**
`daily_cap` (community, default 30), `per_user_invoke_cap` (roast-me + mentions per user per day, default 3 → canned "I'm off the clock" line, no model call), `enabled` kill switch, `max_sass` (`mild` | `medium` | `spicy`).
On CLI rate-limit/usage error → pause until the reported reset (or 1h), post nothing.
One model call at a time (in-process queue, concurrency 1). State (counters, cooldowns, thread counts, pause) in SQLite under `$NEXARA_DATA_DIR`.

**Context sent to the model**: the post/comment text, images (downloaded to tmp via `media:read`),
author display name, last 20 posts by the author (`posts:read`), thread so far for replies.

**Voice rules (system prompt)**: one or two sentences, BBQ-friend energy, punch at choices not people.
Allowed: outfits, haircuts, decor, cooking, opinions, repeat topics (incl. politics), dubious claims ("FACT CHECK: FAKE NEWS").
Never: weight/bodies, health, disability, grief/death, kids in photos, race/religion/sexuality, anyone not opted in.
`spicy` may use tasteful profanity. If nothing funny and safe → output `PASS` → no comment.

**Model call**: `claude -p --output-format json --max-turns 2 --allowedTools Read --append-system-prompt <rules>` with `CLAUDE_CODE_OAUTH_TOKEN` from the `claude_token` secret setting.
Setting `provider` = `claude-cli` | `anthropic-api` (+ `anthropic_api_key` secret) so the owner can move off the subscription without code changes.

**Subscription note (owner-acknowledged risk):** Anthropic's consumer terms do not cover powering
an app for other people with a subscription login; the owner accepts the account risk for a
self-hosted family instance. The `anthropic-api` provider is the compliant path and must stay working.

## 10. Phasing

| Phase | Delivers | Proves |
|---|---|---|
| P1 Core contract | §6 tables, bot accounts, tokens/scopes, webhooks, declarative UI, admin install from a direct package URL | A plugin running anywhere can integrate |
| P2 plugin-host | §7, compose + Helm, install via host | One-click install, isolation |
| P3 Sassybot | §9 (official repo, installed by URL) | Contract is sufficient for a real plugin |
| P4 Marketplace | §8 registry repo, index builder, ratings, Sources/Marketplace tabs, updates, blocklist | Jellyfin-style UX |

Each phase is independently shippable; P3 can run against P1 alone by running Sassybot in its own container.

## 11. Known limits (accepted for v1)
- **Shared host:** a malicious plugin escaping bubblewrap could read other plugins' env/tokens. Upgrade path: per-plugin containers (Nexara emits compose/Helm snippet, or optional runner with socket access).
- **Egress not enforced:** declared + shown only. Upgrade path: host-side HTTP proxy with per-plugin allowlist + `bwrap --unshare-net`.
- **No delivery log/replay**; Celery retries only.
- **Ratings need GitHub accounts.**

## 12. Calls made by the designer (owner please check)
- Instance-wide install, per-community enable/settings/token.
- Bot excluded from private content; subgroup only by explicit admin add.
- Plugin UI declarative only in v1 (no plugin JS).
- Python + Node runtimes only; no native builds at install.
- Default numbers: chance 0.15, cooldown 6h, daily cap 30, per-user cap 3, thread replies 2, rate limit 120/min, index refresh 6h.
- `users.sassybot_opt_out` dropped.
- Missing user prefs → manifest defaults in payload (opt-in safety: Sassybot sees `off`).
- Install/uninstall/sources = instance owner (default-community admin); enable/settings = community admin.

## 13. Left to the builder
Exact route shapes beyond §6.6, frontend component layout, plugin-host process-manager internals,
index builder implementation language (suggest Python script in the Action), Sassybot prompt wording.
