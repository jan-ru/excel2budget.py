# Configuration

## Environment Variables

The backend reads all runtime configuration from environment variables via Pydantic `BaseSettings`. No configuration values are hardcoded in source code.

### Backend

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `info` | Log level: `debug`, `info`, `warning`, `error` |
| `DUCKDB_PATH` | `data/config.duckdb` | Path to DuckDB persistent file |

Invalid values (e.g. `PORT=abc`) cause a `ValidationError` at startup, preventing the application from running with bad configuration.

### Frontend

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL (baked in at build time) |

## 12-Factor App Compliance

The backend follows the [12-factor app](https://12factor.net/) methodology:

### Factor 1 — Codebase

Backend and frontend reside in a single monorepo with separate project roots (`backend/`, `frontend/`).

### Factor 2 — Dependencies

- Backend: all Python dependencies declared in `pyproject.toml` with pinned versions, isolated via virtual environment
- Frontend: all JS/TS dependencies declared in `package.json` with lockfile

### Factor 3 — Config

All runtime settings come from environment variables. The `Settings` class in `backend/app/settings.py` uses Pydantic `BaseSettings` with `@lru_cache` for singleton access.

### Factor 4 — Backing Services

The DuckDB persistent file is treated as an attached resource. Swapping to a different database file requires only changing the `DUCKDB_PATH` environment variable.

### Factor 5 — Build, Release, Run

| Stage | Backend | Frontend |
|---|---|---|
| Build | `pip install .` produces a Python wheel | `vite build` produces static assets in `dist/` |
| Release | Wheel + environment-specific config (env vars) | `dist/` bundle + deployment target |
| Run | `uvicorn backend.app.main:app` reads config from env | Serve `dist/` via any static file server or CDN |

### Factor 6 — Processes

Backend processes are stateless. All persistent state resides in the DuckDB backing service. No session state or request-scoped caches are stored in process memory between requests.

### Factor 7 — Port Binding

The backend exports its HTTP service by binding directly to a port via uvicorn. No external web server container required.

### Factor 8 — Concurrency

Horizontal scaling via multiple uvicorn worker processes. Each worker is stateless and shares only the DuckDB file.

### Factor 9 — Disposability

An async lifespan handler manages startup (logging config, DuckDB connection) and graceful shutdown (connection release). The frontend is disposable by design — closing the browser tab releases all in-memory state.

### Factor 10 — Dev/Prod Parity

Same DuckDB engine (native Python) in all environments. Same DuckDB-WASM and IronCalc-WASM in development and production frontend builds.

### Factor 11 — Logs

Structured JSON logging to stdout via `python-json-logger`. Each log entry contains: `timestamp` (ISO 8601), `level`, `module`, `message`. The application never writes to or manages log files.

### Factor 12 — Admin Processes

The CLI runs as a one-off admin process using the same codebase, Pydantic types, and template registry as the API.

### Observability — Metrics

Prometheus-compatible metrics at `/metrics` via `prometheus-fastapi-instrumentator`:
- `http_requests_total` — counter by method, path, status code
- `http_request_duration_seconds` — histogram of request latency
- `http_requests_in_progress` — gauge of in-flight requests
