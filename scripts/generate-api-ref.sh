#!/usr/bin/env bash
##
# @file scripts/generate-api-ref.sh
# @brief Build the static API reference (docs/docs/developer/api-reference.html).
#
# Gets the OpenAPI schema from OPENAPI_URL (a running backend's /openapi.json)
# when set, otherwise dumps it from the FastAPI app in backend/ (needs the
# backend deps importable). Then renders it with redoc-cli.
##
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/docs/docs/developer/api-reference.html}"
SCHEMA="$(mktemp --suffix=.json)"
trap 'rm -f "$SCHEMA"' EXIT

if [ -n "${OPENAPI_URL:-}" ]; then
  curl -fsS "$OPENAPI_URL" -o "$SCHEMA"
else
  (cd "$ROOT/backend" && python -c \
    'import json,sys; from app.main import app; json.dump(app.openapi(), open(sys.argv[1], "w"))' "$SCHEMA")
fi

# redoc-cli's static single-page command is "bundle".
npx --yes redoc-cli bundle "$SCHEMA" -o "$OUT" --title "Nexara API Reference"
echo "Wrote $OUT"
