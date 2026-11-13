# Troubleshooting

Start with the logs and the health endpoint:

```bash
curl -s http://localhost:8080/healthz          # root path, 200 = healthy
docker compose logs --tail=100 nexara          # Compose
kubectl -n nexara logs deploy/nexara-nexara-api --tail=100   # Helm
```

## Database connection

| Symptom | Fix |
| --- | --- |
| `password authentication failed` | The password in `.env`/secret differs from the one stored in PostgreSQL. The bundled image only reads it on first init; see [password rotation](security.md#database-password). |
| `could not translate host name` | Containers are not on the same network, or the Helm `postgresql.external.host` is wrong. |
| `/healthz` returns 503 | Check which component failed in the response; confirm PostgreSQL is accepting connections (`pg_isready`). |
| Pods crash on start (Helm) | Wait for the startup probe (up to about 150 s for migrations); check `kubectl describe pod` and that `networkPolicy.externalEgressPorts` or egress allows port 5432. |

## WebSocket and SSE

Realtime updates use SSE and WebSockets. If the UI never updates live:

- The reverse proxy must forward `Upgrade`/`Connection` headers and must not
  buffer SSE responses; raise the read timeout (the bundled nginx uses
  3600 s for streams).
- Kubernetes ingress-nginx: add
  `nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"` and
  `nginx.ingress.kubernetes.io/proxy-buffering: "off"`.
- Cloudflare or other CDNs may close idle connections; check their timeouts.
- `ALLOWED_ORIGINS` must include the origin the browser uses.

## Media upload

- `413 Request Entity Too Large`: the bundled nginx accepts up to 520 MB.
  Raise `client_max_body_size` (or `nginx.ingress.kubernetes.io/proxy-body-size`)
  on your own proxy.
- Uploads vanish after restart: the media volume or PVC is not persistent
  (Compose `media` volume, unRAID appdata path, `storage.local.*`).
- Permission denied on the PVC: set a matching `fsGroup`, or use S3.
- Multi-node cluster with local storage: the PVC needs `ReadWriteMany`;
  otherwise pods stay Pending. Prefer `storage.backend=s3`.
- S3 errors: verify `S3_ENDPOINT_URL`, bucket name and credentials.
- Videos stay unprocessed: see Celery below (queue `media`).

## Celery

- Emails, notifications or thumbnails never arrive: check that workers run
  (`kubectl get deploy nexara-nexara-worker`) and consume all queues
  (`worker.queues`: default, maintenance, email, notifications, media).
- Valkey unreachable: workers cannot receive jobs; check `REDIS_URL` or
  `valkey.external.url`.
- Scheduled jobs do not run: beat must run exactly once. Never scale beat
  above 1 replica.
- Queue keeps growing: increase `worker.concurrency` or the worker HPA
  limits; see the queue panels in [Monitoring](monitoring.md).
- Apprise deliveries log `notif.channel.failed`: set `APPRISE_ENCRYPTION_KEY`.

## Memory

- Containers killed with `OOMKilled` (exit 137): raise
  `api.resources.limits.memory` / `worker.resources.limits.memory` (default
  1Gi). Video transcoding is the heaviest workload; lower
  `worker.concurrency` before adding memory.
- On Compose or unRAID, check `docker stats` and give the host swap or more RAM.
- PostgreSQL: bundled limits are 1Gi; raise `postgresql.resources` for large
  communities.

## TLS

- Browser warns about the certificate: the proxy serves the wrong or an
  expired certificate; check `kubectl describe certificate` with cert-manager.
- Redirect loops: the proxy must send `X-Forwarded-Proto`; confirm the
  ingress redirects HTTP only once.
- Mixed content or blocked WebSocket: the site must be reached over HTTPS and
  the CSP `connect-src` must allow `wss://` to your host; see
  [Security](security.md#cors-and-security-headers).
- Login or API calls fail with CORS errors: `ALLOWED_ORIGINS` must match the
  `https://` origin exactly, with no trailing slash.
