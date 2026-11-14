# Kubernetes deployment runbook

Operator guide for deploying Nexara with the Helm chart in `deploy/helm/nexara`.

## Prerequisites

- Kubernetes 1.27+ and Helm 3.12+.
- An ingress controller (for example ingress-nginx) if you expose the API.
- A StorageClass for the PVCs. With `storage.backend=local` and replicas on
  several nodes it must support `ReadWriteMany`; otherwise use S3.
- metrics-server, required by the HPA.
- A CNI that enforces NetworkPolicies, only if `networkPolicy.enabled=true`.

## Install

```bash
helm install nexara deploy/helm/nexara -n nexara --create-namespace \
  --set ingress.enabled=true \
  --set 'ingress.hosts[0].host=nexara.example.com'
kubectl -n nexara rollout status deploy -l app.kubernetes.io/name=nexara
```

Prefer a values file for production: `helm install nexara deploy/helm/nexara -n nexara -f my-values.yaml`.

## Key values

| Key                       | Default            | Purpose                                      |
| ------------------------- | ------------------ | -------------------------------------------- |
| `image.tag`               | chart `appVersion` | Image version to run                         |
| `api.replicas`            | `3`                | API replicas (ignored when `hpa.enabled`)    |
| `worker.replicas`         | `2`                | Celery workers                               |
| `worker.concurrency`      | `4`                | Processes per worker                         |
| `secrets.jwtSecret`       | generated          | Signing secret; set explicitly in production |
| `secrets.existingSecret`  | `""`               | Existing Secret with key `secret-key`        |
| `postgresql.password`     | generated          | Bundled database password                    |
| `env.ALLOWED_ORIGINS`     | `""`               | CORS origins                                 |
| `env.ENABLE_REGISTRATION` | `"true"`           | Open registration                            |
| `storage.backend`         | `local`            | `local` (PVC) or `s3`                        |
| `pdb.enabled`             | `true`             | PodDisruptionBudgets for API and workers     |
| `networkPolicy.enabled`   | `false`            | Restrict pod traffic                         |

The beat scheduler is always a single replica. Never scale it.

Generated secrets are created on first install, reused on upgrade, and kept on
uninstall. Passwords go into the database URL unescaped, so avoid `@`, `/` and `:`.

## External Postgres/Valkey

Bundled Postgres and Valkey are fine for evaluation. For production, use managed services.

```yaml
postgresql:
  enabled: false
  external:
    host: db.example.com
    port: 5432
    database: nexara
    username: nexara
    existingSecret: nexara-db # Secret with key "database-password"
valkey:
  enabled: false
  external:
    url: redis://my-redis:6379
```

The database must exist and its user must be able to create tables.

## Ingress + TLS

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
  hosts:
    - host: nexara.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nexara-tls
      hosts: [nexara.example.com]
```

Create the TLS Secret yourself or let cert-manager issue it via the annotation.

## Autoscaling (HPA)

```yaml
hpa:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilization: 70
  worker:
    enabled: true
    minReplicas: 2
    maxReplicas: 8
    targetCPUUtilization: 70
```

Scaling is CPU-based. Set `api.resources` and `worker.resources` requests
realistically, since utilization is measured against them. Check with
`kubectl -n nexara get hpa`.

## Health probes

The API exposes two endpoints, both served through nginx on the `http` port:

- `/livez`: liveness. Always returns 200 and never touches Postgres, Valkey or
  storage, so a dependency outage does not restart pods. Also used as the startup probe.
- `/healthz`: readiness. Checks Postgres and Valkey (storage is reported but
  non-critical). Returns 503 if either critical dependency is down, so the pod
  is removed from Service endpoints without being restarted.

Tune timing under `api.probes.liveness`, `api.probes.readiness` and
`api.probes.startup`. The default startup budget is 30 x 5s = 150s, which covers
boot and migrations (`alembic upgrade head` runs at API start).

## Upgrade

```bash
helm upgrade nexara deploy/helm/nexara -n nexara -f my-values.yaml --set image.tag=<new-tag>
kubectl -n nexara rollout status deploy -l app.kubernetes.io/name=nexara
```

Back up Postgres first. If a release misbehaves, run `helm rollback nexara <revision> -n nexara`.
Note that database migrations are not reverted by a rollback.

## Uninstall

```bash
helm uninstall nexara -n nexara
```

PVCs and generated Secrets are kept. To delete all data as well:

```bash
kubectl -n nexara delete pvc --all
kubectl delete namespace nexara
```
