# Nexara echo plugin

Stdlib-only example. Replies `echo: <text>` when someone mentions `@echo`.

## Package mode (plugin host, the default)

1. `./package.sh` builds `dist/dev.nexara.echo-<version>.tar.gz` (manifest + `echo.py` at
   the tar root, version from the manifest) and prints its sha256.
2. Serve it where BOTH the Nexara container and the plugin-host container can reach it.
   `localhost` does not work in compose (it is each container's own loopback). Use your
   LAN IP, e.g. `python -m http.server -d dist 9400` and
   `http://192.168.1.20:9400/dev.nexara.echo-0.1.0.tar.gz`, or `host.docker.internal`
   with `extra_hosts: ["host.docker.internal:host-gateway"]` on both services.
3. DEV ONLY settings in `deploy/.env` (all three are needed for an `http://` or private
   URL; real plugins use a public `https://` URL and need none of the insecure flags):
   - `PLUGIN_HOST_URL=http://plugin-host:8700` (core: where the host is) and a
     `PLUGIN_HOST_SECRET`; start with `docker compose --profile plugins up -d`.
   - `PLUGINS_ALLOW_INSECURE_URLS=true` (core: Nexara itself downloads the package to
     read its manifest).
   - `PLUGIN_HOST_ALLOW_INSECURE_DOWNLOADS=true` (plugin host: downloads it again).
4. Admin > Plugins > Install, "Plugin package": the URL and sha256 from step 1; approve the scopes.
5. Enable it in your community. The host starts it and supplies `PORT`, `NEXARA_URL`,
   `NEXARA_TOKEN`, `NEXARA_WEBHOOK_SECRET` and `NEXARA_COMMUNITIES` (nothing is shown to
   copy). Status turns Running within a minute.
6. Post `@echo hello` in a community post: the Echo bot comments `echo: @echo hello`.

## URL mode (you run the process)

1. Core env: `PLUGINS_ALLOW_INSECURE_URLS=true` (dev only, allows http manifest URLs).
2. Start: `HOST=0.0.0.0 python echo.py` (port 9100, override with `PORT`). It serves
   `/nexara-plugin.toml`.
3. Admin > Plugins > Install, "External plugin (advanced)": manifest `http://<host>:9100/nexara-plugin.toml`,
   endpoint `http://<host>:9100/`; approve the scopes.
4. Enable it in your community. The token and webhook secret are shown once (URL mode only).
5. Restart with `HOST=0.0.0.0 NEXARA_URL=http://<core>:8000 NEXARA_TOKEN=nxp_...
   NEXARA_WEBHOOK_SECRET=... python echo.py` (legacy `WEBHOOK_SECRET` also works).
6. Post `@echo hello` as above.

See `docs/docs/developer/plugins.md` for the full contract.

Notes:
- Events carry `community_id`; the plugin picks that community's webhook secret and token
  from `NEXARA_COMMUNITIES` (package mode), so it works in every enabled community.
- Mentions match the bot's real username. If `echo` is already taken, the bot is named
  `echo-bot` (then `echo-bot2`, ...); mention that name instead.
- Without a webhook secret the plugin rejects every webhook.
