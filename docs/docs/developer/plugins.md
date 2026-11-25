# Plugin Contract

Nexara core sends plugins signed webhooks and the plugin calls back with a bot token.
A plugin ships in one of two ways:

- **Package (default):** a `.tar.gz` that the plugin host downloads, installs and runs
  in a sandbox. See [Packaged plugins](#packaged-plugins-plugin-host).
- **External (advanced):** an HTTP service you run yourself. Nexara needs its manifest
  URL and endpoint URL.

A working example of both modes is in `scripts/plugin-echo/`.

## Manifest (`nexara-plugin.toml`)

Max 64 KiB, TOML. In package mode it is read from the tarball root. In external mode
core fetches it from an admin-supplied URL. Both URLs are https and public hosts only,
unless `PLUGINS_ALLOW_INSECURE_URLS=true` is set for development.

```toml
[plugin]
id = "dev.nexara.echo"          # required; lowercase, dotted, e.g. org.name
name = "Echo"                   # required
version = "0.1.0"               # required; semver
description = ""
author = ""
license = ""
homepage = ""
min_core_version = "0.0.0"      # semver; core must be >= this
runtime = "python"              # required: "node" | "python"
entrypoint = "echo.py"          # required; relative path, no ".."
icon = "icon.png"               # optional relative path

[bot]
display_name = "Echo"           # required
username = "echo"               # required
avatar = "bot.png"              # optional relative path

[permissions]
scopes = ["posts:read", "comments:read", "comments:write"]
events = ["mention"]
egress = []                     # informational list of hosts the plugin contacts

[settings.greeting]             # admin-configured, per community
type = "string"                 # boolean | select | number | string | secret
label = "Greeting"

[user_prefs.opt_in]             # per-user, sent with each event as author_prefs
type = "boolean"
label = "Echo my posts"
default = false

[composer_flags.loud]           # per-post flag set in the composer, sent as flags
type = "boolean"
label = "Shout"
```

Field spec keys: `type`, `label` (required), `help`, `default`, `options` (required for
`select`), `min`, `max` (numbers), `max_length` (strings, default and cap 1024).
`default` must fit the type. Keys match `[a-z][a-z0-9_]*`. `secret` is allowed only in
`[settings]`; secrets are never returned by the API. Strings are capped at 1024 chars.
Any validation failure returns `422 invalid_manifest` with `details.errors`.

## Scopes and allowed routes

A bot token may call only these routes, and only with the matching granted scope.
Everything else is `403 plugin_scope_denied`.

| Scope | Routes |
| --- | --- |
| `posts:read` | `GET /api/v1/posts`, `GET /api/v1/posts/{post_id}` |
| `posts:write` | `POST /api/v1/posts` |
| `comments:read` | `GET /api/v1/posts/{post_id}/comments` |
| `comments:write` | `POST /api/v1/posts/{post_id}/comments` |
| `reactions:write` | `POST /api/v1/posts/{post_id}/reactions`, `POST /api/v1/posts/{post_id}/comments/{comment_id}/reactions` |
| `media:read` | `GET /api/v1/media/{media_id}`, `.../file`, `.../thumbnail` |
| `users:read` | `GET /api/v1/users/{user_id}`, `GET /api/v1/users/lookup` |
| `notifications:send` | declared scope; no allowlisted route yet |

Rate limit: 120 requests/minute per token (denied calls count); over it returns `429`.

## Events

Declare them under `[permissions] events`. Known: `post.created`, `comment.created`,
`mention`. Receiving `post.*` needs `posts:read`; `comment.*` needs `comments:read`.
`mention` fires when the bot's username is `@mentioned` in the post or comment, and
needs the same read scope as the underlying content. For comment events
(`comment.created` and comment `mention`), `data.post` is reduced to `{"id": ...}`
unless `posts:read` is also granted. The mention is matched against the bot's real
username, which gets a `-bot` suffix if the manifest username was taken.

Never delivered: anything the bot could not read over the REST API (private posts,
subgroup posts when the bot is not a member, daily-question answers not yet revealed,
authors who blocked the bot or are blocked by it), NSFW posts and NSFW media, and
content authored by a bot. Bots are never treated as adults: the REST API hides NSFW
posts and media from bot tokens too.

### Request

`POST <endpoint_url>`, `Content-Type` JSON body:

```json
{
  "delivery_id": "uuid",
  "event": "post.created | comment.created | mention",
  "community_id": "uuid",
  "occurred_at": "2026-11-23T12:00:00+00:00",
  "data": {
    "post": {"id": "uuid", "content": "...", "visibility": "community",
             "subgroup_id": null, "author_id": "uuid", "created_at": "iso",
             "media": [{"id": "uuid", "mime": "image/png", "url": "/api/v1/media/<id>/file"}]},
    "author": {"id": "uuid", "username": "...", "display_name": "..."},
    "author_prefs": {"opt_in": false},
    "flags": {"loud": true},
    "comment": {"id": "uuid", "content": "...", "parent_id": null,
                "parent_author_id": null, "created_at": "iso"}
  }
}
```

`post` is the full object only with `posts:read`; otherwise (comment events without
it) just `{"id": "uuid"}`. `comment` is present only for comment events. `author_prefs` is the author's user prefs
with defaults filled in; `flags` is this plugin's composer flags on the post.

Headers: `X-Nexara-Delivery` (same as `delivery_id`; use for idempotency),
`X-Nexara-Timestamp` (unix seconds), `X-Nexara-Signature` (`sha256=<hex>`).

## Verifying the signature

`signature = "sha256=" + HMAC_SHA256(webhook_secret, f"{timestamp}." + raw_body)`.
Use the exact raw request bytes (not re-serialized JSON). Reject timestamps more than
300 s from your clock, and compare in constant time.

```python
import hashlib, hmac, time

def verify(secret: str, ts: str, body: bytes, sig: str) -> bool:
    if abs(time.time() - int(ts)) > 300:
        return False
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256)
    return hmac.compare_digest(f"sha256={mac.hexdigest()}", sig)
```

Node (`node:crypto`):

```js
const crypto = require("node:crypto");

function verify(secret, ts, rawBody, sig) {
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
  const mac = crypto.createHmac("sha256", secret)
    .update(`${ts}.`).update(rawBody).digest("hex");
  const a = Buffer.from(`sha256=${mac}`), b = Buffer.from(sig);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

## Delivery and retries

The endpoint URL must be https and resolve to a public host. Otherwise core refuses to
connect and the delivery is silently dropped (a warning in the worker log, no retry),
unless `PLUGINS_ALLOW_INSECURE_URLS` (dev) or the trusted `PLUGIN_HOST_URL` applies.
Install already refuses a plain `http://` endpoint outside those two cases
(`422 endpoint_insecure`).

Timeout 10 s per attempt. Any 2xx (and 3xx, which are not followed) ends the delivery;
other 4xx are dropped without retry. Network errors, timeouts, `5xx`, `408` and `429`
are retried up to 5 times with exponential, jittered backoff. Respond quickly and
process asynchronously; dedupe on `X-Nexara-Delivery`.

## Calling the API (bot token)

On enable, core issues a token (`nxp_...`) and a webhook secret, shown once. Send the
token as `Authorization: Bearer nxp_...`. Re-enabling issues new credentials and
revokes the old token. Disabling revokes the token and deactivates the bot.

```bash
curl -X POST "$NEXARA_URL/api/v1/posts/$POST_ID/comments" \
  -H "Authorization: Bearer $NEXARA_TOKEN" -H "Content-Type: application/json" \
  -d '{"content": "hello"}'
```

## Bot accounts

Each enabled community gets one bot user (`is_bot`, no password, role `member`) named
from `[bot]`; a numeric/`-bot` suffix is added if the username is taken. Bots show a Bot
badge, cannot log in, cannot use admin endpoints, and their content never triggers
plugin events. Uninstalling may optionally hide the bot's content.

## Composer flags and user prefs

`composer_flags` appear in the post composer when the plugin is enabled; values are
validated against the field spec on post creation (`422 invalid_plugin_flag` for an
unknown key or bad value) and stored per plugin id. `user_prefs` are edited by each
user under Settings > Plugins. Both are delivered with every event. `settings` are
set by admins per community.

## Packaged plugins (plugin host)

### Tarball layout

- A gzip tar of at most 50 MB downloaded and 200 MB / 10,000 members extracted.
- `nexara-plugin.toml` and the `entrypoint` file sit at the tar root, not in a
  sub-directory.
- `[plugin] id` must equal the installed id. `version` must equal the version being
  installed (`manifest_mismatch` otherwise).
- Reinstalling the same version with a different sha256 fails with `version_conflict`.
  Bump the version for every new build.
- No links outside the package, devices or absolute paths (`unsafe_archive`).
- Forbidden anywhere in the tree (`forbidden_config_file`): `.npmrc`, `.yarnrc`,
  `.yarnrc.yml`, `.pnpmfile.cjs`, `pip.conf`, `pip.ini`, `uv.toml`, `.python-version`,
  `npm-shrinkwrap.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lock`, `bun.lockb`.
- No top-level `node_modules/` or `.venv/`: the host builds them.

`scripts/plugin-echo/package.sh` is a minimal packaging script.

### Dependencies

Installs run inside the sandbox as the plugin's own uid, with network access but no
install scripts.

- **node:** if `package.json` exists, a `package-lock.json` (lockfileVersion 2 or later)
  is required. The host runs `npm ci --omit=dev --ignore-scripts` against
  `https://registry.npmjs.org/`. Every lock entry must resolve to that registry over
  https with an `integrity` hash. Rejected (`lockfile_unsafe`): git, file, link and
  tarball-URL deps, `inBundle` entries, `workspaces`, `bundle(d)Dependencies`, and
  non-semver ranges in dependencies or `overrides`. There is no lifecycle script, so
  ship compiled JavaScript.
- **python:** the host always creates `.venv` with the image's Python 3.12. An optional
  `requirements.txt` may only hold exact pins, one per line:
  `name[extras]==version`, optional simple markers (`; python_version >= "3.12"`) and
  `--hash=sha256:...` (on every line or on none; with hashes, uv runs
  `--require-hashes`). Options, URLs, paths, `-r`/`-e`, env vars and line
  continuations are rejected (`requirements_unsafe`). Wheels only, from PyPI.
- A failed install reports `deps_failed:exit=N`. Its output is never logged.

### Entrypoint and process

- **python:** `entrypoint` is a script run as `/plugin/.venv/bin/python -u <entrypoint>`.
  The `module:app` form is not supported; start your own server in the script.
- **node:** run as `node <entrypoint>` (Node 22).
- The working directory is `/plugin` (your package, read-only). `/state` is the only
  persistent writable dir. `/tmp` is a private 64 MiB tmpfs.
- Serve `POST /events` on `127.0.0.1:$PORT`. Bind loopback only. The host forwards
  Nexara's webhooks there (body at most 1 MiB, 10 s total per delivery, `X-Nexara-*`
  headers and the body unchanged).
- Limits: 256 processes, 1024 open files, 1 GiB per file. Memory is capped by the
  container.

### Environment

The process gets exactly these variables and nothing from the host:

| Variable | Value |
|---|---|
| `PORT` | Port to listen on (127.0.0.1) |
| `NEXARA_URL` | Base URL of the Nexara API as seen from the host (`http://nexara:8080` in compose) |
| `NEXARA_TOKEN` | Bot token of the default community |
| `NEXARA_WEBHOOK_SECRET` | Webhook secret of the default community |
| `NEXARA_SETTINGS` | JSON object: the default community's plugin settings |
| `NEXARA_COMMUNITIES` | JSON list, one per enabled community: `{community_id, token, webhook_secret, settings, bot_user_id}` |
| `NEXARA_DATA_DIR` | `/state` |
| `HOME` | `/tmp` |
| `PATH` | `/usr/local/bin:/usr/bin:/bin` |

- A plugin enabled in several communities must pick the secret (to verify) and the token
  (to call back) from `NEXARA_COMMUNITIES` by the payload's `community_id`. The
  `NEXARA_TOKEN`/`NEXARA_WEBHOOK_SECRET` pair only covers the default community, and
  other communities' events would fail verification.
- Tokens rotate every time Nexara pushes the plugin (enable, disable elsewhere, settings
  change, host restart), and the process is restarted with the new env. Never persist
  tokens.

### Network, logs and failures

- **Egress (compose):** plugins reach the public internet, Docker DNS and `NEXARA_URL`
  only. All loopback (including the plugin's own port: do not call yourself over
  127.0.0.1), the container's own addresses, and private, link-local and metadata
  ranges are blocked. Helm uses a NetworkPolicy instead.
- **Logs:** stdout and stderr, the last 200 lines (2,000 chars each), are shown under
  Admin > Plugins. The plugin's own token, secret and settings values are redacted.
- **Crashes:** restarts back off for 1, 2, 4, 8 and 16 s. More than 5 crashes in 10
  minutes marks the plugin `failed` and alerts admins. To retry, disable it and enable
  it again.
- **Uninstall:** removes the code. Plugin state in `/state` is purged only when "delete
  content" is chosen and the host is reachable.

## Admin install flow

### Package (default)

1. Instance owner: Admin > Plugins > Install, "Plugin package". Enter the package URL and
   its sha256. Core downloads it, checks the sha256, reads the manifest and shows the
   scopes, events and egress. The owner must approve every requested scope.
2. Enable the plugin in a community. Core creates the bot, a token and a webhook secret,
   and pushes them to the plugin host. Nothing is shown to copy. Nothing runs until the
   first community is enabled.
3. The status turns Running within a minute. Settings changes are pushed the same way.

Errors: `plugin_host_not_configured` (422, `PLUGIN_HOST_URL` not set),
`package_url_invalid` / `package_fetch_failed` / `package_too_large` /
`package_sha256_mismatch` (422). Host-side failures show on the plugin as a status code
(for example `manifest_mismatch`, `lockfile_unsafe`, `deps_failed:exit=1`).

### External plugin (advanced)

1. Run the plugin so it serves `nexara-plugin.toml` and an endpoint URL.
2. Instance owner: Admin > Plugins > Install, "External plugin (advanced)". Enter the
   manifest URL and endpoint URL; core fetches and validates the manifest, then shows
   scopes, events and egress. The owner must approve every requested scope or install
   fails with `422 scopes_not_approved`.
3. Enable the plugin in a community. Core creates the bot, a token and a webhook
   secret, shown once. Give them to the plugin (for example `NEXARA_TOKEN`,
   `NEXARA_WEBHOOK_SECRET`).
4. Configure settings if any. In URL mode settings are stored but not sent, so configure
   the plugin directly (for example with environment variables). Posts and comments now
   trigger deliveries.

Errors: `plugin_already_installed` (409), `plugin_incompatible` (422, core older than
`min_core_version`), `manifest_url_invalid` / `manifest_fetch_failed` (422),
`endpoint_insecure` (422, http endpoint without the dev flag or plugin host origin).
