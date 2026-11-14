# Kubernetes (Helm)

Install from the local chart path. No Helm repository is published.

```bash
helm install nexara ./deploy/helm/nexara -n nexara --create-namespace \
  --set ingress.enabled=true \
  --set 'ingress.hosts[0].host=nexara.example.com' \
  --set 'env.ALLOWED_ORIGINS=https://nexara.example.com'
helm lint ./deploy/helm/nexara
```

All keys below come from `deploy/helm/nexara/values.yaml`. With release name
`nexara` in the chart `nexara`, resources are named `nexara-nexara-<part>`
(for example `nexara-nexara-api`). Adjust if you pick another release name.

The image runs the API (port 8080), Celery workers and Celery beat. Beat is
always a single replica.

## Secrets

Generated on first install, reused on upgrade, kept on uninstall. For
production create them yourself:

```bash
kubectl -n nexara create secret generic nexara-app \
  --from-literal=secret-key="$(openssl rand -hex 32)"
helm upgrade --install nexara ./deploy/helm/nexara -n nexara \
  --set secrets.existingSecret=nexara-app
```

The secret needs key `secret-key` and optionally `apprise-encryption-key`.
Avoid `@`, `/` and `:` in generated database passwords, they are placed in the
database URL unescaped.

## External PostgreSQL

```yaml
postgresql:
  enabled: false
  external:
    host: db.example.com
    port: 5432
    database: nexara
    username: nexara
    existingSecret: nexara-db   # key "database-password"
```

```bash
kubectl -n nexara create secret generic nexara-db \
  --from-literal=database-password='<password>'
helm upgrade --install nexara ./deploy/helm/nexara -n nexara -f values-prod.yaml
```

The database and role must exist; the role must be able to create tables.
When `networkPolicy.enabled=true`, egress to `postgresql.external.port` is
allowed.

## External S3 storage

```yaml
storage:
  backend: s3
  s3:
    endpointUrl: https://s3.example.com
    bucket: nexara
    existingSecret: nexara-s3   # keys "s3-access-key", "s3-secret-key"
```

```bash
kubectl -n nexara create secret generic nexara-s3 \
  --from-literal=s3-access-key='<key>' --from-literal=s3-secret-key='<secret>'
```

S3 is the right choice for multi-node clusters. With `storage.backend=local`
media lives on a PVC (`storage.local.size`) whose default access mode is
`ReadWriteMany`; use `ReadWriteOnce` only on single-node clusters.

## Replicas and autoscaling

| Key | Default | Meaning |
| --- | --- | --- |
| `api.replicas` | 3 | Used only when `hpa.enabled=false` |
| `hpa.enabled` | true | CPU-based autoscaling of the API |
| `hpa.minReplicas` / `hpa.maxReplicas` | 3 / 10 | API bounds |
| `hpa.targetCPUUtilization` | 70 | Percent of requests |
| `hpa.worker.*` | 2 / 8, 70 | Celery worker autoscaling |
| `worker.concurrency` | 4 | Processes per worker pod |
| `pdb.minAvailable` | 1 | PodDisruptionBudget for API and workers |

HPA needs metrics-server. Example:

```bash
helm upgrade nexara ./deploy/helm/nexara -n nexara --reuse-values \
  --set hpa.maxReplicas=20 --set hpa.worker.maxReplicas=12
kubectl -n nexara get hpa
```

To pin the replica count, set `hpa.enabled=false` and `api.replicas=N`.

## Prometheus and Grafana

The API serves Prometheus metrics at `/metrics` on port 8080. The chart does
not ship a ServiceMonitor. With a plain Prometheus, scrape the API pods:

```yaml
scrape_configs:
  - job_name: nexara-api
    metrics_path: /metrics
    kubernetes_sd_configs: [{role: pod, namespaces: {names: [nexara]}}]
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_component]
        regex: api
        action: keep
```

If you expose `/metrics` through the ingress, restrict it; it is not meant
to be public. Import `deploy/grafana/nexara-dashboard.json` as described in
[Monitoring](monitoring.md) and set the `namespace` variable to `nexara`.

## Backup and restore

Data lives in the PostgreSQL PVC (`nexara-nexara-postgresql`) and, with local
storage, the media PVC. Valkey is a cache/broker and need not be backed up.

Database dump (works for the bundled database):

```bash
kubectl -n nexara exec nexara-nexara-postgresql-0 -- \
  pg_dump -U nexara -Fc nexara > nexara-db.dump
```

Restore into an empty database:

```bash
kubectl -n nexara exec -i nexara-nexara-postgresql-0 -- \
  pg_restore -U nexara -d nexara --clean --if-exists < nexara-db.dump
```

PV backup: if your CSI driver supports snapshots, create a
`VolumeSnapshot` of each PVC (`kubectl -n nexara get pvc` lists them) and
restore by creating a new PVC with that snapshot as `dataSource`, then point
the chart at it. Without snapshots, copy the media PVC with a temporary pod:

```bash
kubectl -n nexara run media-backup --rm -i --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"b","image":"alpine","command":["tar","czf","-","-C","/data","."],"volumeMounts":[{"name":"d","mountPath":"/data"}]}],"volumes":[{"name":"d","persistentVolumeClaim":{"claimName":"<media-pvc>"}}]}}' \
  --image=alpine > nexara-media.tgz
```

Replace `<media-pvc>` with the claim listed by `kubectl get pvc`. Restore by
reversing the tar direction with `tar xzf -`. Also back up the secrets
(`secret-key`, `apprise-encryption-key`).

## Upgrading

```bash
helm upgrade nexara ./deploy/helm/nexara -n nexara --reuse-values --set image.tag=<version>
kubectl -n nexara rollout status deploy/nexara-nexara-api
```

See [Security](security.md) for NetworkPolicy and TLS, and
[Troubleshooting](troubleshooting.md) when pods do not become ready.
