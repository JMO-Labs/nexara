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

The app is then served through the bundled proxy on `http://localhost:8080`.

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
healthcheck uses it. In development, the Next.js dev server proxies
`/healthz` to the backend at `http://localhost:8000/healthz`.
