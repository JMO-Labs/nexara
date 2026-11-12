# Monitoring with Grafana

Nexara ships a Grafana dashboard at `deploy/grafana/nexara-dashboard.json`.

## Enable backend metrics

The backend exposes Prometheus metrics at `/metrics` (HTTP metrics via
`prometheus-fastapi-instrumentator`, plus `nexara_*` application gauges and
counters defined in `backend/app/core/metrics.py`). Add a scrape job named
`nexara-api` pointing at the API service.

## Exporters

The dashboard also expects, deployed separately:

- Node Exporter (CPU, memory, disk, network)
- postgres_exporter (`pg_*` metrics), with `--collector.stat_statements`
  and the `pg_stat_statements` extension for the Query latency panel
- A Celery exporter (`celery_*` metrics)
- kube-state-metrics (for the `namespace` variable)

## Import

1. Grafana: Dashboards, Import, upload `nexara-dashboard.json`.
2. Select your Prometheus datasource.
3. Adjust the `namespace`, `community_id` and `refresh_interval` variables.

`namespace` filters the Nexara app metrics (`http_*`, `nexara_*`). Choose
**All** on Docker Compose or other deployments without a `namespace` label.
Exporter metrics (`pg_*`, `celery_*`, `node_*`) are not namespace-filtered.
`community_id` only filters metrics that carry that label (today: the
per-community storage table).

Defaults: last 6 hours, refresh every 30 s. Clicking a panel's link opens it
full-size with the current time range. Deployments are annotated from
`nexara_build_info`; tag manual annotations `nexara` + `incident`.

## Interpreting and troubleshooting

- **No data in a panel:** the matching exporter or scrape job is missing.
  Check Prometheus, Status, Targets.
- **Error rate above 5%:** inspect API logs and the 4xx/WAF panels.
- **Status codes are grouped:** the instrumentator exports `2xx`/`4xx`/`5xx`
  only, so the Security row shows 4xx totals (403s are not isolated).
- **Queue depth growing:** workers saturated; see Worker utilization.
- **Login 4xx / audit log:** derived from HTTP handler labels; they are
  approximations until dedicated counters exist.
- **Per-community storage empty:** `nexara_storage_used_bytes` currently has
  no `community_id` label.
