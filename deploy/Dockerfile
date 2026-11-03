# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
#
# Two images from one file (build from the repository root: docker compose -f deploy/compose.yaml build):
#   app  the room server (FastAPI + the Python engine), one process, the room store on /data
#   web  Caddy: HTTPS, the built client, and /rooms proxied to app; it writes no access log (no client IP addresses)
# The repository layout is kept under /app, because the server finds scenarios and content relative to it.

FROM node:22-bookworm-slim AS client
WORKDIR /app
COPY package.json package-lock.json ./
COPY packages/engine/package.json packages/engine/
COPY packages/ui/package.json packages/ui/
RUN npm ci --no-audit --no-fund
COPY packages/engine packages/engine
COPY packages/ui packages/ui
COPY content content
COPY packages/scenarios packages/scenarios
RUN npm run build

FROM python:3.13-slim-bookworm AS app
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
COPY packages/engine-py packages/engine-py
COPY packages/server packages/server
COPY packages/scenarios packages/scenarios
COPY content content
RUN cd packages/server && uv sync --locked --no-dev
RUN useradd --system --uid 10001 fairflow && mkdir -p /data && chown fairflow /data
USER fairflow
ENV FAIRFLOW_STORE=/data/rooms.sqlite
EXPOSE 8000
WORKDIR /app/packages/server
# One worker only: a room's lock and its live connections live in this process (ADR 0012).
# --no-access-log and --log-level warning keep client addresses out of the log (packages/server/README.md).
CMD ["/app/packages/server/.venv/bin/uvicorn", "fairflow_server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--log-level", "warning"]

FROM caddy:2-alpine AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=client /app/packages/ui/dist /srv
