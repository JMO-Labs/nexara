# Docker Compose

This page covers the Compose stack in `deploy/docker-compose.yml`. See the
[deployment guide](deployment-guide.md) for other platforms. Nexara is designed for self-hosted deployment with minimal infrastructure.

## Containers

The primary deployment method uses two containers:

| Container     | Contents                                              |
| ------------- | ----------------------------------------------------- |
| `nexara`      | Nginx + FastAPI + Celery + Valkey (via supervisord)   |
| `nexara-db`   | PostgreSQL 16 Alpine                                  |

### Quick Start

```bash
# Clone and navigate to deploy directory
cd deploy

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, POSTGRES_PASSWORD, etc.)

# Start the stack
docker compose up -d
```

### Environment Variables

| Variable             | Required | Default | Description                      |
| -------------------- | -------- | ------- | -------------------------------- |
| `SECRET_KEY`         | Yes      |         | Random secret (openssl rand -hex 32) |
| `POSTGRES_PASSWORD`  | Yes      |         | Database password                |
| `ALLOWED_ORIGINS`    | Yes      |         | Your domain (CORS)               |
| `HTTP_PORT`          | No       | 8080    | Host port for the app            |
| `STORAGE_BACKEND`    | No       | local   | `local` or `s3`                  |
| `SMTP_HOST`          | No       |         | SMTP server for email            |

### Reverse Proxy

Nexara does **not** bundle a reverse proxy. Use your existing:

- Nginx Proxy Manager
- Caddy
- Traefik
- Cloudflare Tunnel

Point your proxy to `http://{host_ip}:{HTTP_PORT}` and enable SSL.

## Volumes to Back Up

| Volume          | Contents                          | Priority     |
| --------------- | --------------------------------- | ------------ |
| `postgres_data` | All community data                | **Critical** |
| `media`         | Uploaded photos and videos        | **Critical** |

## Backup and restore

Back up both volumes. Dump the database with `pg_dump` instead of copying
live files.

```bash
cd deploy
# Database
docker compose exec -T nexara-db pg_dump -U nexara -Fc nexara > nexara-db.dump
# Media (volume name is prefixed by the project name, "nexara")
docker run --rm -v nexara_media:/data -v "$PWD":/backup alpine \
  tar czf /backup/nexara-media.tgz -C /data .
```

Restore into a fresh stack:

```bash
docker compose up -d nexara-db
docker compose exec -T nexara-db pg_restore -U nexara -d nexara --clean --if-exists < nexara-db.dump
docker run --rm -v nexara_media:/data -v "$PWD":/backup alpine \
  tar xzf /backup/nexara-media.tgz -C /data
docker compose up -d
```

Keep `.env` (especially `SECRET_KEY` and `APPRISE_ENCRYPTION_KEY`) with your
backups; without them sessions and stored Apprise URLs cannot be recovered.
Test a restore before you need it.

## Upgrading

```bash
docker compose pull && docker compose up -d
```

Migrations run on start. Take a backup first.

## Health check

`GET /healthz` (root path, not `/api/v1/healthz`) returns 200 when the
database, Valkey and storage are healthy, 503 otherwise. The compose
healthcheck uses it.

## Plugin host (optional)

The `plugin-host` service installs and sandboxes plugin packages (bubblewrap,
one uid per plugin). It is off by default; enable it with a compose profile:

```bash
# in .env: PLUGIN_HOST_SECRET=<openssl rand -hex 32>  (required, no default)
#          PLUGIN_HOST_URL=http://plugin-host:8700
docker compose --profile plugins up -d
```

- Shares only the `nexara-plugins` network with `nexara`; it cannot reach
  `nexara-db`. Nexara reaches it at `PLUGIN_HOST_URL` (`http://plugin-host:8700`).
- The container runs as root with `cap_drop: ALL` plus `SETUID`, `SETGID`,
  `CHOWN`, `KILL`, `NET_ADMIN`, `seccomp=unconfined`, `apparmor=unconfined`,
  `no-new-privileges`, a read-only root filesystem, a sized `/tmp` tmpfs and
  the `plugin_data` volume at `/data`. bubblewrap needs user namespaces, which
  the default seccomp/AppArmor profiles block; the host applies its own seccomp
  filter to every plugin instead. Do not add `systempaths=unconfined`.
- Root has no `DAC_OVERRIDE`/`FOWNER`: it cannot read or change files a plugin
  uid owns. Do not "fix" permission errors by adding capabilities; the host
  logs the failing path (`install error: PermissionError errno=13 path=...`).
- Egress: `PLUGIN_EGRESS_FILTER` (default `true`) installs iptables rules in
  the plugin-host container's own network namespace (this is what `NET_ADMIN`
  is for). Plugins may reach the internet, Docker DNS and `NEXARA_URL` only;
  loopback (including the host's control API), the container's own addresses
  and private/link-local/metadata ranges are dropped. The rules follow
  `nexara`'s IP when it is recreated (re-checked at most once a minute). If
  they cannot be installed, plugins report `sandbox_unavailable`. Set it to `false` only together with removing
  `NET_ADMIN` from `cap_add`.
- `PLUGIN_HOST_ALLOW_INSECURE_DOWNLOADS` (default `false`) is **development
  only**: it lets the host download packages over `http://` and from
  private/loopback addresses (packages are still sha256-checked). For a local
  test package you also need core `PLUGINS_ALLOW_INSECURE_URLS=true`, since
  Nexara downloads the package first; see `scripts/plugin-echo/README.md`.
- `TRUSTED_PROXIES`: never trust a whole Docker range (for example
  `172.16.0.0/12` for a Traefik container). plugin-host's address on the
  `nexara-plugins` bridge would match, and plugins could spoof
  `X-Forwarded-For`. List your proxy's exact address instead.
- `pids_limit: 512` and `mem_limit` (`PLUGIN_HOST_MEM_LIMIT`, default `1g`)
  bound all plugins combined.
- Known gap: a disk quota for each plugin's `/state` is **not enforced**; a
  plugin can fill the `plugin_data` volume.
- Uninstalling while the host is unreachable removes the plugin's code at the
  next poll but keeps its `/state` even if "delete content" was chosen.

GitLab CI: the host's sandbox tests need a privileged docker-in-docker runner.
The job runs only when the project variable `PLUGIN_HOST_SANDBOX_CI=true` is
set and a runner tagged `privileged` exists; otherwise a
`test:plugin-host:skipped` job notes that they did not run.
