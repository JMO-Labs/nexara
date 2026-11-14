#!/usr/bin/env bash
##
# @file scripts/check-docs-helm.sh
# @brief Renders the chart with the value sets used in docs/docs/deployment/kubernetes.md.
# @return 0 when every combination renders; skips (0) if helm is missing.
##
set -eu
command -v helm >/dev/null || { echo "SKIP: helm not installed"; exit 0; }
c="$(dirname "$0")/../deploy/helm/nexara"
helm template nexara "$c" -n nexara --set ingress.enabled=true \
  --set 'ingress.hosts[0].host=nexara.example.com' \
  --set 'env.ALLOWED_ORIGINS=https://nexara.example.com' >/dev/null
helm template nexara "$c" --set secrets.existingSecret=nexara-app >/dev/null
helm template nexara "$c" --set postgresql.enabled=false \
  --set postgresql.external.host=db.example.com \
  --set postgresql.external.existingSecret=nexara-db >/dev/null
helm template nexara "$c" --set storage.backend=s3 \
  --set storage.s3.endpointUrl=https://s3.example.com \
  --set storage.s3.existingSecret=nexara-s3 >/dev/null
helm template nexara "$c" --set hpa.maxReplicas=20 --set hpa.worker.maxReplicas=12 \
  --set networkPolicy.enabled=true --set image.tag=1.0.0 >/dev/null
echo OK
