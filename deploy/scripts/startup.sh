#!/bin/sh
# =============================================================================
# Nexara — Container Entrypoint Script
# =============================================================================
#
# Runs before supervisord to ensure the environment is ready:
#   1. Wait for PostgreSQL to accept connections
#   2. Run Alembic database migrations
#   3. Launch supervisord (which manages all long-running processes)
# =============================================================================

set -e

echo "=== Nexara startup ==="

# ── 1. Wait for PostgreSQL ───────────────────────────────────────────────────
echo "Waiting for PostgreSQL..."

DB_HOST="${DATABASE_URL#*@}"
DB_HOST="${DB_HOST%%:*}"
DB_PORT="${DATABASE_URL#*:}"
DB_PORT="${DB_PORT%%/*}"
# Extract numeric port from the asyncpg URL
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*@[^:]*:\([0-9]*\).*/\1/p')

RETRIES=30
until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U nexara > /dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        echo "ERROR: PostgreSQL not reachable after 30 attempts. Exiting."
        exit 1
    fi
    echo "  PostgreSQL not ready, retrying in 2s... ($RETRIES attempts left)"
    sleep 2
done
echo "PostgreSQL is ready."

# ── 2. Run database migrations ───────────────────────────────────────────────
echo "Running Alembic migrations..."

# Alembic needs the sync DATABASE_URL (postgresql:// not postgresql+asyncpg://)
export ALEMBIC_DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgresql+asyncpg://|postgresql://|')

cd /app
alembic upgrade head

echo "Migrations complete."

# ── 2b. JWT signing keys ─────────────────────────────────────────────────────
# Generate once, before the workers start, so every uvicorn/celery process
# signs and verifies with the same key pair (per-process ephemeral keys made
# ~half of authenticated requests fail with 401). /data is a volume, so keys
# survive container recreation.
python -c "from app.core.config import get_settings; from app.core.security import _load_or_generate_rsa_keys; _load_or_generate_rsa_keys(get_settings())"
chown nexara:nexara /data /data/*.pem 2>/dev/null || true
echo "JWT keys ready."

# ── 3. Launch supervisord ────────────────────────────────────────────────────
echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisord.conf
