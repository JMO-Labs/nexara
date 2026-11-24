# Plugin Contract

Plugins are external HTTP services. Nexara core sends them signed webhooks and the
plugin calls back with a bot token. A working example lives in `scripts/plugin-echo/`.

## Manifest (`nexara-plugin.toml`)

Max 64 KiB, TOML. Fetched by core from an admin-supplied URL (https only, public
hosts only, unless `PLUGINS_ALLOW_INSECURE_URLS=true` for development).

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

Never delivered: private posts, NSFW posts, content authored by a bot, content the bot
could not see (subgroup posts when the bot is not a member), and authors who blocked
the bot or are blocked by it.

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

## Admin install flow

1. Run the plugin so it serves `nexara-plugin.toml` and an endpoint URL.
2. Instance owner: Admin > Plugins > Install from URL. Enter the manifest URL and
   endpoint URL; core fetches and validates the manifest, then shows scopes, events and
   egress. The owner must approve every requested scope or install fails with
   `422 scopes_not_approved`.
3. Enable the plugin in a community. Core creates the bot, a token and a webhook
   secret, shown once. Give them to the plugin (for example `NEXARA_TOKEN`,
   `WEBHOOK_SECRET`).
4. Configure settings if any. Posts and comments now trigger deliveries.

Errors: `plugin_already_installed` (409), `plugin_incompatible` (422, core older than
`min_core_version`), `manifest_url_invalid` / `manifest_fetch_failed` (422).
