# Nexara Helm chart

```bash
helm install nexara deploy/helm/nexara -n nexara --create-namespace \
  --set ingress.enabled=true --set 'ingress.hosts[0].host=nexara.example.com'
helm lint deploy/helm/nexara
```

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
| `pluginHost` | `enabled` (false), `image.*`, `existingSecret`, `persistence.size`, `egressPorts`, `resources` | Optional sandboxed plugin runner on :8700; sets `PLUGIN_HOST_URL`/`PLUGIN_HOST_SECRET` on nexara pods. |

Generated secrets are created on first install and reused on upgrade (via `lookup`,
kept on uninstall). Set
`secrets.jwtSecret` / `postgresql.password` or reference an existing Secret.
Set them explicitly for production. Passwords are placed in the database URL
unescaped, so avoid `@`, `/` and `:` in them. With `storage.backend=local`, use a
StorageClass supporting `ReadWriteMany` (see `storage.local.accessModes`) when
running replicas on multiple nodes.

## Plugin host

`pluginHost.enabled=true` deploys one replica (RWO `/data` PVC, `/tmp` emptyDir)
running as root with seccomp and AppArmor `Unconfined` and caps
`SETUID,SETGID,CHOWN,KILL` (bubblewrap needs user namespaces); `/proc` stays masked,
the SA token is not mounted and the rootfs is read-only. The namespace must permit
this (Pod Security `baseline`/`privileged`, not `restricted`). The memory limit is in
`pluginHost.resources`; a pids limit is a kubelet setting (`--pod-max-pids`).
`PLUGIN_HOST_SECRET` comes from `pluginHost.existingSecret` (key
`plugin-host-secret`) or is generated once and kept.

With `networkPolicy.enabled`, only api/worker reach the host, and the host may reach
DNS, the API and the internet except `networkPolicy.privateCidrs`. That exclusion is
what blocks Postgres/Valkey: add your pod/service CIDRs if they are outside the
defaults, or the deny is incomplete. Requires a CNI that enforces NetworkPolicy.

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
