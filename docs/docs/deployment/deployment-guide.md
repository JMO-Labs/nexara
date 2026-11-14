# Deployment Guide

Nexara is self-hosted. Pick the platform that matches your infrastructure.

## Pages

- [Docker Compose](docker-compose.md): two containers, recommended for most.
- [Kubernetes (Helm)](kubernetes.md): scaling, external PostgreSQL and S3.
- [unRAID](unraid.md): Community Applications templates.
- [Monitoring](monitoring.md): Prometheus metrics and the Grafana dashboard.
- [Security](security.md): TLS, secret rotation, network and header hardening.
- [Troubleshooting](troubleshooting.md): common failures and fixes.

## Feature matrix

| Feature                    | Docker Compose | Kubernetes (Helm)     | unRAID           |
| -------------------------- | -------------- | --------------------- | ---------------- |
| Setup effort               | Low            | Medium                | Low (GUI)        |
| Horizontal scaling         | No             | Yes (HPA, 3 to 10)    | No               |
| High availability          | No             | Yes (PDB, anti-affinity) | No            |
| External PostgreSQL        | Edit compose   | `postgresql.external` | Database URL     |
| External S3 media          | `STORAGE_BACKEND=s3` | `storage.backend=s3` | Env variables |
| NetworkPolicy              | n/a            | `networkPolicy.enabled` | n/a            |
| Built-in TLS               | No (use proxy) | Ingress TLS           | No (use proxy)   |
| Bundled Valkey             | Yes            | Yes (or external)     | Yes (or separate) |
| Backup tooling             | Volume dumps   | PVC snapshots, `pg_dump` | Appdata backup |

## Quick-start comparison

=== "Docker Compose"

    ```bash
    cd deploy && cp .env.example .env   # set SECRET_KEY, POSTGRES_PASSWORD
    docker compose up -d                # app on :8080
    ```

=== "Kubernetes"

    ```bash
    helm install nexara ./deploy/helm/nexara -n nexara --create-namespace \
      --set 'ingress.hosts[0].host=nexara.example.com' --set ingress.enabled=true
    ```

=== "unRAID"

    Copy the XML templates from `deploy/unraid/` to
    `/boot/config/plugins/dockerMan/templates-user/` and install
    `nexara-postgres`, then `nexara`.

No Helm repository is published; always install from the local chart path
`./deploy/helm/nexara` of a repository checkout.

## Health check

The health endpoint is at the root path, not under `/api/v1`:

```
GET /healthz
```

It returns HTTP 200 when the database, Valkey and storage are healthy, and
503 otherwise.
