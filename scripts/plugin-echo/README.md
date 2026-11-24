# Nexara echo plugin

Stdlib-only example. Replies `echo: <text>` when someone mentions `@echo`.

## Run

1. Core env: `PLUGINS_ALLOW_INSECURE_URLS=true` (dev only, allows http manifest URLs).
2. Start: `python echo.py` (port 9100, override with `PORT`). It serves
   `/nexara-plugin.toml`.
3. Admin > Plugins > Install from URL: manifest `http://<host>:9100/nexara-plugin.toml`,
   endpoint `http://<host>:9100/`; approve the scopes.
4. Enable it in your community. The token and webhook secret are shown once.
5. Restart with `NEXARA_URL=http://<core>:8000 NEXARA_TOKEN=nxp_... WEBHOOK_SECRET=... python echo.py`.
6. Post `@echo hello` in a community post: the Echo bot comments `echo: @echo hello`.

See `docs/docs/developer/plugins.md` for the full contract.
