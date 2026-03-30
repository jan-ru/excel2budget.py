# Deployment

## Overview

The application is containerized as two Docker services orchestrated via `docker-compose.yml`:

- **backend** — FastAPI + DuckDB, served by uvicorn on port 8000
- **frontend** — Vite-built static files served by nginx on port 80, with `/api` proxied to the backend

## Prerequisites

- Docker and Docker Compose (v2+)
- A domain name (for production with SSL)

## Local Testing

```bash
docker compose up --build
```

The app will be available at `http://localhost`. The frontend serves on port 80 and proxies API requests to the backend container.

To stop:

```bash
docker compose down
```

## Container Architecture

```
┌─────────────────────────────────────────────┐
│              nginx (port 80)                │
│  Static files: /usr/share/nginx/html        │
│  Proxy: /api/* → backend:8000               │
│  Proxy: /openapi.json → backend:8000        │
│  Proxy: /metrics → backend:8000             │
│  SPA fallback: /* → index.html              │
├─────────────────────────────────────────────┤
│           backend (port 8000)               │
│  FastAPI + uvicorn                          │
│  DuckDB persistent file: /data/config.duckdb│
│  Volume: duckdb-data:/data                  │
└─────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Python 3.12 slim, deps installed with uv, runs uvicorn |
| `frontend/Dockerfile` | Multi-stage: Node 18 build → nginx:alpine serving `dist/` |
| `frontend/nginx.conf` | nginx config: static files, API proxy, SPA fallback, asset caching |
| `docker-compose.yml` | Two services, named volume for DuckDB persistence |
| `.dockerignore` | Excludes .git, node_modules, .venv, tests, etc. from build context |

## Environment Variables

### Backend

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `info` | Log level: debug, info, warning, error |
| `DUCKDB_PATH` | `/data/config.duckdb` | Path to DuckDB persistent file (inside container) |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `""` (empty) | API base URL. Empty means relative paths, so nginx proxy handles routing. |

## Deploying with Coolify on Hetzner

[Coolify](https://coolify.io/) is a self-hosted PaaS that manages Docker deployments with automatic SSL via Traefik.

### Setup

1. Connect your Git repository in Coolify's dashboard
2. Select "Docker Compose" as the build pack
3. Coolify will detect `docker-compose.yml` at the repo root
4. Configure your domain in Coolify's UI — it handles SSL/TLS termination automatically

### Persistent Storage

DuckDB data is stored in a named Docker volume (`duckdb-data`). This survives container restarts and redeployments. Coolify preserves named volumes across deployments by default.

### Health Check

The backend container includes a health check that polls `/openapi.json` every 30 seconds. Coolify uses this to determine container readiness.

### Updating

Push to your Git repo's main branch. Coolify can be configured to auto-deploy on push, or you can trigger a manual deployment from the dashboard.

## Production Considerations

- The frontend nginx config sets 1-year cache headers on static assets (JS, CSS, WASM, fonts). Vite's content-hashed filenames ensure cache busting on new deployments.
- The backend is stateless except for the DuckDB file. Horizontal scaling would require a shared database, but for a single-instance deployment this is not a concern.
- No raw financial data crosses the network boundary — all processing happens in the browser. The backend only serves templates, documentation, and configuration metadata.
