# Nexara Helm chart

```bash
helm install nexara deploy/helm/nexara -n nexara --create-namespace \
  --set ingress.enabled=true --set 'ingress.hosts[0].host=nexara.example.com'
helm lint deploy/helm/nexara
```

For a full operator guide see the
[Kubernetes deployment runbook](../../../docs/docs/deploy/kubernetes.md).

The single `ghcr.io/jmo-labs/nexara` image runs the API (default entrypoint,
port 8080), the Celery worker and Celery beat (command overrides).

## Values

| Section | Key values | Notes |
|---|---|---|
| `image` | `registry`, `repository`, `tag`, `pullPolicy` | `tag` defaults to `appVersion`. |
| `api` | `replicas` (3), `resources`, `affinity` | Soft pod anti-affinity by default. Ignored when `hpa.enabled`. |
| `worker` | `replicas` (2), `queues`, `concurrency`, `resources` | |
| `beat` | `resources` | Always 1 replica (`Recreate` strategy). |
| `valkey` | `enabled`, `resources`, `persistence.size`, `external.url` | |
| `postgresql` | `enabled`, `resources`, `persistence.size`, `external.*` | |
| `ingress` | `enabled` (false), `className`, `hosts`, `tls`, `annotations` | |
| `hpa` | `enabled`, `minReplicas`, `maxReplicas`, `targetCPUUtilization` (70) | CPU-based, API only. |
| `secrets` | `jwtSecret`, `existingSecret` | Generated randomly if empty. |
| `env` | `COMMUNITY_DEFAULT`, `LOG_LEVEL`, ... | Free-form map rendered into a ConfigMap. |
| `storage` | `backend` (`local`/`s3`), `local.size`, `s3.*` | |

Generated secrets are created on first install and reused on upgrade (via `lookup`,
kept on uninstall). Set
`secrets.jwtSecret` / `postgresql.password` or reference an existing Secret.
Set them explicitly for production. Passwords are placed in the database URL
unescaped, so avoid `@`, `/` and `:` in them. With `storage.backend=local`, use a
StorageClass supporting `ReadWriteMany` (see `storage.local.accessModes`) when
running replicas on multiple nodes.

## External database

```yaml
postgresql:
  enabled: false
  external:
    host: db.example.com
    port: 5432
    database: nexara
    username: nexara
    existingSecret: nexara-db   # Secret with key "database-password"
```

The database must exist and the user must be able to create tables
(run `alembic upgrade head` from the API image).

## External storage (S3)

```yaml
storage:
  backend: s3
  s3:
    endpointUrl: https://s3.example.com
    bucket: nexara
    existingSecret: nexara-s3   # keys "s3-access-key", "s3-secret-key"
```

Or set `accessKey` / `secretKey` inline (stored in a chart-managed Secret).
With `backend: local`, media lives on a PVC. The default access mode is
`ReadWriteMany`, which needs an RWX-capable StorageClass. Use
`storage.local.accessModes={ReadWriteOnce}` only on single-node clusters;
otherwise use S3.

## External Valkey / Redis

```yaml
valkey:
  enabled: false
  external:
    url: redis://my-redis:6379
```
