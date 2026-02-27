# =============================================================================
# Nexara App Container — Multi-Stage Alpine Build
# =============================================================================
#
# Build context: repository root (set in docker-compose.yml)
#
# Stage 1 (frontend-builder): Install Node deps, build Nuxt static output
# Stage 2 (python-builder):   Install Python dependencies with uv
# Stage 3 (runtime):          Alpine with Nginx, supervisord, Valkey, ffmpeg
# =============================================================================

# ── Stage 1: Build Frontend ──────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
RUN npm run generate

# ── Stage 2: Build Python dependencies ──────────────────────────────────────
FROM python:3.12-alpine AS python-builder

WORKDIR /build

RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev \
    && pip install --no-cache-dir uv

COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-alpine AS runtime

RUN apk add --no-cache \
    nginx \
    supervisor \
    valkey \
    ffmpeg \
    libmagic \
    postgresql-client \
    wget \
    && rm -rf /var/cache/apk/*

RUN adduser -D -u 1001 nexara

WORKDIR /app

# Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.12/site-packages \
     /usr/local/lib/python3.12/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Frontend static output from builder stage
COPY --from=frontend-builder /build/.output/public /usr/share/nginx/html

# Backend source
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY backend/pyproject.toml ./

# Configuration files
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/supervisord/supervisord.conf /etc/supervisord.conf
COPY deploy/supervisord/conf.d/ /etc/supervisor.d/
COPY deploy/valkey/valkey.conf /etc/valkey/valkey.conf

# Startup script
COPY deploy/scripts/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Media storage volume + Nginx runtime dirs
RUN mkdir -p /data/media /run/nginx /var/log/nginx \
    && chown -R nexara:nexara /data/media /run/nginx

EXPOSE 8080 9090

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --spider -q http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["/app/startup.sh"]
