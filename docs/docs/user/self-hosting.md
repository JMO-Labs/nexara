# Self-Hosting

Nexara is container-native. The supported ways to run it are Docker Compose
(single host) and the Helm chart (Kubernetes).

## Requirements

- A Linux host with Docker 24+ and the Compose plugin, or a Kubernetes 1.27+
  cluster with an ingress controller.
- PostgreSQL 16 and Valkey (a Redis-compatible store). Both are included in
  the Compose file.
- A domain name and TLS termination if the instance is exposed to the internet.
- Roughly 2 GB of RAM and enough disk for uploaded media.

## Docker Compose

```bash
cd deploy
cp .env.example .env
# edit .env: set secrets, database password, and public URL
docker compose up -d
```

The reverse proxy listens on port `8080` by default. Put your own TLS proxy
(Caddy, Traefik, nginx) in front of it for HTTPS. Database migrations run on
startup; check the backend container logs if the site does not come up.

To upgrade, pull the new images and restart:

```bash
docker compose pull
docker compose up -d
```

## Helm

The chart lives in `deploy/helm/nexara/`.

```bash
helm install nexara deploy/helm/nexara \
  --namespace nexara --create-namespace \
  -f my-values.yaml
```

Use your values file to set the ingress host, image tags, persistent volume
sizes, and references to Kubernetes Secrets. Never put secrets directly in a
values file that is committed to version control.

## Environment configuration

| Variable | Purpose |
| -------- | ------- |
| `DATABASE_URL` | PostgreSQL connection string |
| `VALKEY_URL` | Valkey/Redis connection string used for cache, queues, realtime |
| `SECRET_KEY` | Signing key for sessions and tokens; generate a long random value |
| `PUBLIC_URL` | External URL used in links, emails, and push notifications |
| `SMTP_*` | Outgoing email settings for invitations and notifications |

Consult `deploy/.env.example` for the complete, current list.

## Backups

Back up the PostgreSQL database and the media volume together so they stay
consistent. A nightly `pg_dump` plus a snapshot of the media directory is
enough for most communities. Test restores periodically.

## Troubleshooting

- **Login loops**: `PUBLIC_URL` does not match the address in the browser.
- **No emails**: verify the SMTP settings and check the email worker logs.
- **Slow uploads**: the media worker transcodes in the background; check that
  the worker container is running.
