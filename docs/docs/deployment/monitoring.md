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
- postgres_exporter (`pg_*` metrics)
- A Celery exporter (`celery_*` metrics)
- kube-state-metrics (for the `namespace` variable)

## Import

1. Grafana: Dashboards, Import, upload `nexara-dashboard.json`.
2. Select your Prometheus datasource.
3. Adjust the `namespace`, `community_id` and `refresh_interval` variables.

Defaults: last 6 hours, refresh every 30 s. Clicking a panel's link opens it
full-size with the current time range. Deployments are annotated from
`nexara_build_info`; tag manual annotations `nexara` + `incident`.

## Interpreting and troubleshooting

- **No data in a panel:** the matching exporter or scrape job is missing.
  Check Prometheus, Status, Targets.
- **Error rate above 5%:** inspect API logs and the 403/WAF panels.
- **Queue depth growing:** workers saturated; see Worker utilization.
- **Failed logins / audit log:** derived from HTTP handler labels; they are
  approximations until dedicated counters exist.
- **Per-community storage empty:** `nexara_storage_used_bytes` currently has
  no `community_id` label.
