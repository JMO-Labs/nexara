# =============================================================================
# Nexara App Container — Multi-Stage Alpine Build
# =============================================================================
#
# Build context: repository root (set in docker-compose.yml)
#
# Stage 1 (frontend-builder): Install Node deps, build Next.js standalone
# Stage 2 (python-builder):   Install Python dependencies with uv
# Stage 3 (runtime):          Alpine with Nginx, supervisord, Valkey, Node, ffmpeg
#
# After the Nuxt → Next 16 cutover, the frontend is a Node-served standalone
# Next app (port 3000 internally) proxied by Nginx alongside Uvicorn.
# =============================================================================

# ── Stage 1: Build Frontend ──────────────────────────────────────────────────
FROM node:25-alpine3.22 AS frontend-builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Build Python dependencies ──────────────────────────────────────
FROM python:3.12-alpine AS python-builder

WORKDIR /build

RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev \
    && pip install --no-cache-dir uv

COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

# ── Stage 3: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-alpine AS runtime

RUN apk add --no-cache \
    nginx \
    supervisor \
    valkey \
    ffmpeg \
    libmagic \
    nodejs \
    postgresql-client \
    wget \
    && rm -rf /var/cache/apk/*

RUN adduser -D -u 1001 nexara

WORKDIR /app

# Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.12/site-packages \
     /usr/local/lib/python3.12/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Frontend (Next standalone): server + static + public assets
COPY --from=frontend-builder --chown=nexara:nexara /build/.next/standalone /app/frontend
COPY --from=frontend-builder --chown=nexara:nexara /build/.next/static /app/frontend/.next/static
COPY --from=frontend-builder --chown=nexara:nexara /build/public /app/frontend/public

# Backend source
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY backend/data/ ./data/
COPY backend/pyproject.toml ./

# Configuration files
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/supervisord/supervisord.conf /etc/supervisord.conf
COPY deploy/supervisord/conf.d/ /etc/supervisor.d/
COPY deploy/valkey/valkey.conf /etc/valkey/valkey.conf

# Runtime dirs
RUN mkdir -p /run/nginx /data/media \
    && chown -R nexara:nexara /data/media /app

EXPOSE 8080 9090

CMD ["supervisord", "-c", "/etc/supervisord.conf", "-n"]
