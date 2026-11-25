# @file plugin-host.Dockerfile
# @brief Nexara plugin-host image: bubblewrap sandbox + node 22 / python / uv runtimes.
#
# Runs as root on purpose (per-plugin uids via setuid; see deploy docs for the
# required cap_add/security_opt). Build context = repo root.
#   docker build -f deploy/docker/plugin-host.Dockerfile -t nexara-plugin-host .
#   docker build --target test ...   # adds dev deps + tests (CI)

FROM node:22.23.5-bookworm-slim@sha256:be979e5523c76fa4d5ca4ebd3099078f220aa47ec39c48ad5b5df9314debd6eb AS node
FROM ghcr.io/astral-sh/uv:0.5.31@sha256:7bff3c3776ec467fc1437960f2c469d8beb30f536a6465a3350c647ccd260ec2 AS uv

FROM python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64 AS base
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bubblewrap util-linux libseccomp2 ca-certificates tini iptables \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=uv /uv /uvx /usr/local/bin/
# bwrap mountpoints (rootfs is read-only at runtime); /data is the volume
RUN mkdir -p /plugin /state /data
# XTABLES_LOCKFILE: rootfs is read-only at runtime; /tmp is a tmpfs
ENV UV_PROJECT_ENVIRONMENT=/opt/venv PYTHONUNBUFFERED=1 XTABLES_LOCKFILE=/tmp/xtables.lock
WORKDIR /app
COPY plugin-host/pyproject.toml plugin-host/uv.lock ./

FROM base AS test
RUN uv sync --frozen
COPY plugin-host/host ./host
COPY plugin-host/tests ./tests
CMD ["/opt/venv/bin/pytest", "-q", "-p", "no:cacheprovider"]

FROM base AS runtime
RUN uv sync --frozen --no-dev
COPY plugin-host/host ./host
EXPOSE 8700
VOLUME /data
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 8700), 3)"]
# tini as PID 1 reaps the sandbox processes bwrap leaves behind (compose and k8s alike)
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/venv/bin/uvicorn", "host.main:app", "--host", "0.0.0.0", "--port", "8700"]
