# Nexara echo plugin

Stdlib-only example. Replies `echo: <text>` when someone mentions `@echo`.

## Run

1. Core env: `PLUGINS_ALLOW_INSECURE_URLS=true` (dev only, allows http manifest URLs).
2. Start: `python echo.py` (port 9100, override with `PORT`). It serves
   `/nexara-plugin.toml`.
3. Admin > Plugins > Install from URL: manifest `http://<host>:9100/nexara-plugin.toml`,
   endpoint `http://<host>:9100/`; approve the scopes.
4. Enable it in your community. The token and webhook secret are shown once.
5. Restart with `NEXARA_URL=http://<core>:8000 NEXARA_TOKEN=nxp_... NEXARA_WEBHOOK_SECRET=... python echo.py` (legacy `WEBHOOK_SECRET` also works).
6. Post `@echo hello` in a community post: the Echo bot comments `echo: @echo hello`.

## Package for plugin-host

`./package.sh` builds `dist/dev.nexara.echo-<version>.tar.gz` (manifest + `echo.py` at the
tar root, version from the manifest) and prints its sha256. Serve it over http (e.g.
`python -m http.server -d dist`), set `PLUGIN_HOST_ALLOW_INSECURE_DOWNLOADS=true` on the
host (DEV ONLY), and install with the package URL + sha256. The host supplies `PORT`,
`NEXARA_URL`, `NEXARA_TOKEN` and `NEXARA_WEBHOOK_SECRET`.

See `docs/docs/developer/plugins.md` for the full contract.

Note: mentions match the bot's real username. If `echo` is already taken, the bot is
named `echo-bot` (then `echo-bot2`, ...); mention that name instead. Without a
webhook secret the plugin rejects every webhook.
