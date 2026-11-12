# Deployment Guide

Nexara is designed for self-hosted deployment with minimal infrastructure.

## Docker Compose (Recommended)

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

## Kubernetes (Helm)

For Kubernetes deployments, use the Helm chart in `deploy/helm/nexara/`:

```bash
helm install nexara deploy/helm/nexara/ \
  --set secretKey="$(openssl rand -hex 32)" \
  --set postgresql.password="$(openssl rand -hex 16)"
```

## unRAID

Nexara provides Community Applications templates for one-click installation
on unRAID. See the unRAID template XMLs in `deploy/unraid/`.

## Volumes to Back Up

| Volume          | Contents                          | Priority     |
| --------------- | --------------------------------- | ------------ |
| `postgres_data` | All community data                | **Critical** |
| `media`         | Uploaded photos and videos        | **Critical** |

## Health Check

The health endpoint is mounted at the **root** path, not under `/api/v1`:

```
GET /healthz
```

- **Path:** `/healthz` (not `/api/v1/healthz`)
- **Response:** HTTP 200 when all components (DB, Valkey, storage) are healthy, HTTP 503 otherwise
- In development, the Next.js dev server proxies `/healthz` to the backend at `http://localhost:8000/healthz`
