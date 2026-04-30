#!/usr/bin/env bash
# @file scripts/dev-start.sh
# @brief One-command dev environment launcher.
#
# Starts PostgreSQL, Valkey, generates JWT keys if needed,
# runs Alembic migrations, and launches the FastAPI backend
# and Nuxt frontend with proper proxy configuration.
#
# Usage:
#   ./scripts/dev-start.sh          # start everything
#   ./scripts/dev-start.sh --stop   # tear down running services
#   ./scripts/dev-start.sh --reset  # stop + start fresh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
DATA_DIR="${ROOT_DIR}/.dev-data"

BACKEND_PORT=8000
FRONTEND_PORT=3000
PG_CONTAINER="${NEXARA_PG_CONTAINER:-nexara-dev-db}"
VK_CONTAINER="${NEXARA_VK_CONTAINER:-nexara-dev-valkey}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[dev]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC}  $*"; }
warn() { echo -e "${YELLOW}[!]${NC}  $*"; }
err()  { echo -e "${RED}[err]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"${port}" 2>/dev/null || true)
  if [[ -n "${pids}" ]]; then
    echo "${pids}" | xargs kill -9 2>/dev/null || true
    log "Killed processes on port ${port}"
  fi
}

wait_for_port() {
  local port=$1 max_wait=${2:-30} elapsed=0
  while ! nc -z 127.0.0.1 "${port}" 2>/dev/null; do
    sleep 1
    elapsed=$((elapsed + 1))
    if [[ ${elapsed} -ge ${max_wait} ]]; then
      err "Timed out waiting for port ${port}"
      return 1
    fi
  done
}

ensure_container() {
  local name=$1 image=$2; shift 2
  if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
    ok "${name} already running"
    return
  fi
  if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
    docker start "${name}" >/dev/null
    ok "${name} started (existing container)"
    return
  fi
  docker run -d --name "${name}" "$@" "${image}" >/dev/null
  ok "${name} created and started"
}

# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

do_stop() {
  log "Stopping dev services..."
  kill_port ${BACKEND_PORT}
  kill_port ${FRONTEND_PORT}
  kill_port 3001
  kill_port 3002
  docker stop ${PG_CONTAINER} ${VK_CONTAINER} 2>/dev/null || true
  ok "All services stopped"
}

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

do_start() {
  log "=== Nexara Dev Environment ==="

  # 1) Kill stale processes on dev ports
  kill_port ${BACKEND_PORT}
  kill_port ${FRONTEND_PORT}
  kill_port 3001
  kill_port 3002

  # 2) Data directory
  mkdir -p "${DATA_DIR}/jwt" "${DATA_DIR}/media"

  # 3) PostgreSQL
  log "Starting PostgreSQL..."
  ensure_container ${PG_CONTAINER} postgres:16-alpine \
    -p 5432:5432 \
    -e POSTGRES_USER=nexara \
    -e POSTGRES_PASSWORD=nexara \
    -e POSTGRES_DB=nexara \
    -v "${DATA_DIR}/pgdata:/var/lib/postgresql/data"
  wait_for_port 5432

  # 4) Valkey (Redis-compatible)
  log "Starting Valkey..."
  ensure_container ${VK_CONTAINER} valkey/valkey:8-alpine \
    -p 6379:6379
  wait_for_port 6379

  # 5) JWT keys
  local jwt_priv="${DATA_DIR}/jwt/jwt_private.pem"
  local jwt_pub="${DATA_DIR}/jwt/jwt_public.pem"
  if [[ ! -f "${jwt_priv}" ]]; then
    log "Generating JWT RS256 key pair..."
    openssl genpkey -algorithm RSA -out "${jwt_priv}" -pkeyopt rsa_keygen_bits:2048 2>/dev/null
    openssl rsa -in "${jwt_priv}" -pubout -out "${jwt_pub}" 2>/dev/null
    ok "JWT keys generated"
  else
    ok "JWT keys exist"
  fi

  # 6) Backend venv
  if [[ ! -d "${BACKEND_DIR}/.venv" ]]; then
    log "Creating backend venv..."
    cd "${BACKEND_DIR}"
    uv venv .venv
    uv pip install -r requirements.txt
    ok "Backend venv ready"
  fi

  # 7) Alembic migrations
  log "Running database migrations..."
  cd "${BACKEND_DIR}"
  source .venv/bin/activate
  JWT_PRIVATE_KEY_PATH="${jwt_priv}" \
  JWT_PUBLIC_KEY_PATH="${jwt_pub}" \
  LOCAL_STORAGE_PATH="${DATA_DIR}/media" \
  HIBP_CHECK_ENABLED=false \
  APP_ENV=development \
  ENABLE_METRICS=false \
    alembic upgrade head 2>&1 | tail -3
  ok "Migrations complete"

  # 8) Start backend
  log "Starting FastAPI backend on :${BACKEND_PORT}..."
  cd "${BACKEND_DIR}"
  JWT_PRIVATE_KEY_PATH="${jwt_priv}" \
  JWT_PUBLIC_KEY_PATH="${jwt_pub}" \
  LOCAL_STORAGE_PATH="${DATA_DIR}/media" \
  HIBP_CHECK_ENABLED=false \
  APP_ENV=development \
  DEBUG=true \
  ENABLE_METRICS=false \
  ALLOWED_ORIGINS="http://localhost:${FRONTEND_PORT},http://$(hostname).local:${FRONTEND_PORT},http://$(hostname -I 2>/dev/null | awk '{print $1}'):${FRONTEND_PORT}" \
    nohup .venv/bin/python -m uvicorn app.main:app \
      --host 0.0.0.0 --port ${BACKEND_PORT} \
      > "${DATA_DIR}/backend.log" 2>&1 &
  local backend_pid=$!
  echo "${backend_pid}" > "${DATA_DIR}/backend.pid"
  wait_for_port ${BACKEND_PORT} 15
  ok "Backend running (PID ${backend_pid})"

  # 9) Frontend deps
  if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
    log "Installing frontend dependencies..."
    cd "${FRONTEND_DIR}"
    npm ci
    ok "Frontend deps installed"
  fi

  # 10) Start frontend
  log "Starting Next.js frontend on :${FRONTEND_PORT}..."
  cd "${FRONTEND_DIR}"
  nohup npm run dev -- --hostname 0.0.0.0 --port ${FRONTEND_PORT} \
    > "${DATA_DIR}/frontend.log" 2>&1 &
  local frontend_pid=$!
  echo "${frontend_pid}" > "${DATA_DIR}/frontend.pid"
  wait_for_port ${FRONTEND_PORT} 30
  ok "Frontend running (PID ${frontend_pid})"

  # 11) Health check
  log "Running health check..."
  local health
  health=$(curl -sf http://localhost:${BACKEND_PORT}/healthz 2>/dev/null || echo '{"status":"unreachable"}')
  ok "Backend health: ${health}"

  echo ""
  echo -e "${GREEN}=== Dev environment is ready ===${NC}"
  echo -e "  Frontend:  ${CYAN}http://localhost:${FRONTEND_PORT}${NC}"
  echo -e "  Backend:   ${CYAN}http://localhost:${BACKEND_PORT}${NC}"
  echo -e "  API docs:  ${CYAN}http://localhost:${BACKEND_PORT}/docs${NC}"
  echo -e "  Logs:      ${CYAN}${DATA_DIR}/backend.log${NC}"
  echo -e "             ${CYAN}${DATA_DIR}/frontend.log${NC}"
  echo ""
  echo -e "  Stop with: ${YELLOW}./scripts/dev-start.sh --stop${NC}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:-}" in
  --stop)
    do_stop
    ;;
  --reset)
    do_stop
    sleep 1
    do_start
    ;;
  *)
    do_start
    ;;
esac
