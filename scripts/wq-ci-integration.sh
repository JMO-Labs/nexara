#!/usr/bin/env bash
##
# @file scripts/wq-ci-integration.sh
# @brief Run backend/tests/integration against dockerized Postgres 16 + Valkey.
#        Writes junit-int.xml and appends to coverage.xml in the repo root.
#        No docker: fails when $CI is set, otherwise warns and skips.
##
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PG=nexara-ci-pg; VK=nexara-ci-valkey

if ! command -v docker >/dev/null; then
  if [ -n "${CI:-}" ]; then echo "ERROR: docker required in CI for integration tests" >&2; exit 1; fi
  echo "WARNING: docker not found; skipping integration tests" >&2; exit 0
fi

cleanup() { docker rm -f "$PG" "$VK" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# Role is superuser, so CREATEDB (needed by migration tests) is implied.
docker run -d --name "$PG" -p 5432:5432 -e POSTGRES_USER=nexara -e POSTGRES_PASSWORD=nexara \
  -e POSTGRES_DB=nexara_test postgres:16 >/dev/null || exit 1
docker run -d --name "$VK" -p 6379:6379 valkey/valkey:8 >/dev/null || exit 1

ready=0
for _ in $(seq 1 60); do
  if docker exec "$PG" pg_isready -U nexara -d nexara_test >/dev/null 2>&1 \
     && docker exec "$VK" valkey-cli ping >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "ERROR: services not ready after 60s" >&2; exit 1; }

export DATABASE_URL=postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test
export REDIS_URL=redis://127.0.0.1:6379
# Tests expect a migrated schema (communities etc.); migration tests use scratch DBs.
(cd backend && "${ALEMBIC_BIN:-.venv/bin/alembic}" upgrade head) || { echo "ERROR: alembic upgrade failed" >&2; exit 1; }
cd backend && "${PYTEST_BIN:-.venv/bin/pytest}" tests/integration -q --cov=app --cov-append \
  --cov-report=xml:"$ROOT/coverage.xml" --junitxml="$ROOT/junit-int.xml"
