# Self-Hosting Guide

Run Nexara on your own server with Docker Compose.

## Requirements

- Docker with the Compose plugin
- PostgreSQL 16 (bundled in the default compose stack)
- Valkey (Redis-compatible; bundled in the default compose stack)
- A reverse proxy for HTTPS (Nginx Proxy Manager, Caddy, Traefik)

## Quick start

```bash
cd deploy
cp .env.example .env
# edit .env: set SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d
```

Generate the required secrets with `openssl rand -hex 32` (`SECRET_KEY`)
and `openssl rand -hex 16` (`POSTGRES_PASSWORD`).

The built-in proxy listens on port **8080** (`HTTP_PORT`). Open
`http://localhost:8080`, or put your HTTPS reverse proxy in front of it.

## Key environment variables

All variables live in `deploy/.env.example`.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Session signing and JWT secret (required) |
| `POSTGRES_PASSWORD` | Database password (required) |
| `HTTP_PORT` | Host port for HTTP traffic (default `8080`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `STORAGE_BACKEND` | `local` or `s3` |
| `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` | S3 storage settings |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Email delivery |
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | Default SSO provider |
| `ENABLE_REGISTRATION`, `REQUIRE_INVITE` | Control who can sign up |

See [SSO / OIDC](../developer/sso-oidc.md) for provider setup.

## Upgrades

Pull the new images and restart:

```bash
cd deploy
docker compose pull
docker compose up -d
```

Database migrations normally run on start. To run them manually:

```bash
alembic upgrade head
```

Back up your database before every upgrade.

## Backups

Dump the database with `pg_dump`:

```bash
docker compose exec -T postgres pg_dump -U nexara nexara > nexara-backup.sql
```

Adjust the service, user and database names to match your compose file.
Restore with `psql < nexara-backup.sql`. With `STORAGE_BACKEND=local`, also
back up the uploads volume; with `s3`, back up the bucket.

## Kubernetes (Helm)

A Helm chart is provided in `deploy/helm/nexara/`. See the chart's
`values.yaml` for configuration options.

## Next steps

Read the [FAQ](faq.md).
