# Security

## TLS

Nexara serves plain HTTP on port 8080. Terminate TLS in front of it.

- **Docker Compose / unRAID:** use Caddy, Traefik, Nginx Proxy Manager or a
  Cloudflare Tunnel pointing at `http://<host>:8080`. Forward the
  `Upgrade` and `Connection` headers (WebSocket) and disable response
  buffering for SSE. Redirect HTTP to HTTPS and send
  `Strict-Transport-Security`.
- **Kubernetes:** enable the ingress with a certificate, for example with
  cert-manager:

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
  hosts:
    - host: nexara.example.com
      paths: [{path: /, pathType: Prefix}]
  tls:
    - secretName: nexara-tls
      hosts: [nexara.example.com]
```

## Rotating secrets

Back up first. Rotate one secret at a time and verify `/healthz` after each.

### Database password

- **Compose:** change the role password, then update `.env` and restart.

  ```bash
  docker compose exec nexara-db psql -U nexara -c "ALTER USER nexara PASSWORD '<new>'"
  # edit POSTGRES_PASSWORD in .env
  docker compose up -d
  ```

- **Helm, bundled database:** the password is only read when the data
  directory is first created, so also run `ALTER USER` inside the pod, then
  `helm upgrade --set postgresql.password=<new>`.
- **Helm, external database:** change it on the server, update the secret
  named in `postgresql.external.existingSecret` (key `database-password`) and
  `kubectl rollout restart` the api, worker and beat deployments.

### JWT / signing secret (`SECRET_KEY`)

Changing it signs out every user (existing tokens become invalid). Generate
`openssl rand -hex 32`, set `SECRET_KEY` in `.env`, or update key `secret-key`
in the secret from `secrets.existingSecret` (or `--set secrets.jwtSecret=...`),
then restart all Nexara pods. Do not rotate `APPRISE_ENCRYPTION_KEY` this way:
stored Apprise URLs are encrypted with it and become unreadable.

## NetworkPolicy (Kubernetes)

Requires a CNI that enforces policies (Calico, Cilium).

```bash
helm upgrade nexara ./deploy/helm/nexara -n nexara --reuse-values \
  --set networkPolicy.enabled=true
```

The chart then limits ingress to the API port, lets only the app pods reach
PostgreSQL and Valkey, and allows egress to DNS, the data stores and
`networkPolicy.externalEgressPorts` (default 443, 587, 465 for HTTPS, SMTP,
S3, push). Set `networkPolicy.apiIngressFrom` to your ingress controller's
namespace/pod selector so only it can reach the API. Add ports to
`externalEgressPorts` for non-standard SMTP or S3 endpoints.

## Firewall

Expose only 443 (and 80 for redirects) from the proxy. Do not publish
`HTTP_PORT` (8080), `METRICS_PORT` (9090) or PostgreSQL (5432) to the internet.
Bind to localhost or a private interface when the proxy runs on the same host.

## CORS and security headers

Set `ALLOWED_ORIGINS` (`.env`) or `env.ALLOWED_ORIGINS` (Helm) to your exact
HTTPS origin(s), comma separated. If empty, the backend allows all origins.

The API sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy` and `Permissions-Policy`. It does not set a
`Content-Security-Policy`; add one at the reverse proxy and test it against
your setup, for example:

```
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; \
  media-src 'self' blob:; connect-src 'self' wss://nexara.example.com; \
  frame-ancestors 'none'
```

Add your S3 or CDN host to `img-src`/`media-src` when media is served from
there.

## Rate limiting

The API rate limits per client IP: `RATE_LIMIT_DEFAULT` (default
`600/minute`) and a stricter `RATE_LIMIT_AUTH` (default `10/minute`) for
authentication endpoints. Override them through the environment (`.env`, or
`env.RATE_LIMIT_AUTH` in Helm values). Add proxy-level limits for extra
protection.

The client IP comes from `X-Forwarded-For`, believed only from addresses in
`TRUSTED_PROXIES` (default `127.0.0.1/32,::1/128`, the bundled nginx). Behind
your own reverse proxy, ingress controller or cloudflared, add its IP or CIDR
(`env.TRUSTED_PROXIES` in Helm, e.g. the ingress pod CIDR), otherwise every
member shares the proxy's IP and its rate-limit bucket. `*` is not supported.
Do not set uvicorn's `FORWARDED_ALLOW_IPS` wider than `TRUSTED_PROXIES`.
With Cloudflare also set `CF_ACCESS_ENABLED=true` so `CF-Connecting-IP` is
used; the origin must then only be reachable through Cloudflare.
