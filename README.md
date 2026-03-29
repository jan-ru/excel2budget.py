# Data Conversion Tool

A two-tier data conversion platform that transforms financial data between source formats and accounting package import formats. The frontend runs entirely in the browser via WebAssembly ([IronCalc](https://www.ironcalc.com/) for spreadsheet rendering, [DuckDB WASM](https://duckdb.org/docs/api/wasm/overview) for SQL transformations). The backend ([FastAPI](https://fastapi.tiangolo.com/)) serves template definitions, documentation generation, and configuration persistence. Raw financial data never leaves the browser.

## Overview

This tool is part of a larger system of application modules, each handling a specific conversion use case:

| Module | Purpose |
|---|---|
| **excel2budget** | Convert Excel budget files (wide month columns) into accounting package budget import formats |
| **update_forecast** | Update forecast data in accounting packages *(planned)* |
| **reporting_actuals** | Report actuals data from accounting packages *(planned)* |

All modules share a common Documentation Module that generates standardized documentation artifacts via a generic `ApplicationContext` interface.

### Supported Accounting Packages

- Twinfield (full budget template)
- Exact (stub template)
- Afas (stub template)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (TypeScript + Vite)                 │
│  @ui5/webcomponents · DuckDB-WASM · IronCalc-WASM · SheetJS │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Excel    │ SQL      │ IronCalc │ Exporters│ Pipeline        │
│ Importer │ Generator│ Preview  │ CSV/XLSX │ Orchestrator    │
│ (SheetJS)│          │          │ PDF      │                 │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│  Memory Guard · Data Validator · XSS Sanitizer              │
├─────────────────────────┬────────────────────────────────────┤
│      API Client         │  REST/JSON (metadata only)         │
└─────────────────────────┼────────────────────────────────────┘
                          │
┌─────────────────────────┴────────────────────────────────────┐
│                  Backend (FastAPI + Python)                    │
├──────────┬──────────────┬──────────────┬─────────────────────┤
│ Template │ Documentation│ Config Store │ CLI                  │
│ Registry │ Module       │ (DuckDB)     │ (dev/ops)            │
└──────────┴──────────────┴──────────────┴─────────────────────┘
```

### Data Privacy Boundary

All raw financial data (Excel cell values, transformed rows, exported files) stays in the browser. Only metadata and aggregates are sent to the backend for documentation generation.

## Project Structure

```
├── backend/                       # FastAPI Python backend
│   ├── run.py                     # uvicorn entry point (port binding)
│   ├── app/
│   │   ├── main.py                # FastAPI entry point + lifespan handler
│   │   ├── settings.py            # Pydantic BaseSettings (env config)
│   │   ├── logging_config.py      # JSON structured logging (python-json-logger)
│   │   ├── cli.py                 # CLI entry point (dev/ops)
│   │   ├── core/
│   │   │   ├── types.py           # Pydantic models (single source of truth)
│   │   │   └── api_models.py      # API request/response models
│   │   ├── routers/
│   │   │   ├── templates.py       # Template registry endpoints
│   │   │   ├── documentation.py   # Documentation generation endpoint
│   │   │   └── configurations.py  # Config CRUD endpoints
│   │   ├── templates/             # Accounting package templates
│   │   │   ├── registry.py
│   │   │   ├── afas/budget.py
│   │   │   ├── exact/budget.py
│   │   │   └── twinfield/budget.py
│   │   ├── documentation/         # 7-artifact documentation generator
│   │   └── persistence/
│   │       └── config_store.py    # DuckDB config persistence
│   ├── tests/                     # Hypothesis property tests + integration
│   └── pyproject.toml
│
├── frontend/                      # TypeScript browser application
│   ├── src/
│   │   ├── main.ts                # Entry point
│   │   ├── types/api.d.ts         # Auto-generated from OpenAPI (DO NOT EDIT)
│   │   ├── api/client.ts          # Typed API client
│   │   ├── import/excel-importer.ts
│   │   ├── transform/sql-generator.ts
│   │   ├── engine/
│   │   │   ├── duckdb-engine.ts   # DuckDB-WASM wrapper
│   │   │   └── ironcalc-engine.ts # IronCalc-WASM wrapper
│   │   ├── validation/data-validator.ts
│   │   ├── security/xss-sanitizer.ts
│   │   ├── guards/memory-guard.ts
│   │   ├── export/
│   │   │   ├── csv-excel-exporter.ts
│   │   │   └── pdf-exporter.ts
│   │   ├── pipeline/
│   │   │   ├── orchestrator.ts    # Pipeline coordination
│   │   │   └── context-builder.ts # ApplicationContext builder
│   │   └── ui/                    # @ui5/webcomponents screens
│   │       ├── app.ts
│   │       ├── screens/           # Upload, Preview, Config, Transform, Output, Docs
│   │       └── components/        # Header, Error banner
│   ├── scripts/generate-types.ts  # OpenAPI → TypeScript type generation
│   ├── tests/                     # fast-check property tests + integration
│   ├── package.json
│   └── vite.config.ts
│
├── src/                           # Original monolithic Python codebase (legacy)
├── tests/                         # Original test suite (legacy)
└── README.md
```

## Key Concepts

### Type Synchronization Pipeline

Types flow from Pydantic models on the backend through the auto-generated OpenAPI spec to TypeScript types via `openapi-typescript`. This establishes a single source of truth for the API contract:

```
Pydantic models → OpenAPI spec (/openapi.json) → openapi-typescript → frontend/src/types/api.d.ts
```

### DuckDB Dual Usage

DuckDB is used on both sides: native Python on the backend for configuration persistence, and DuckDB-WASM in the browser for SQL-driven data transformation. No SQLite dependency.

### Documentation Module

A reusable, application-agnostic module that generates 7 documentation artifacts per conversion configuration via a generic `ApplicationContext`: ArchiMate diagram, BPMN diagram, input/output/transform descriptions, control table, and user instruction.

### Control Table

Every conversion produces a reconciliation sheet proving input totals equal output totals, ensuring no data is lost or corrupted.

### 12-Factor App Compliance

The backend follows the [12-factor app](https://12factor.net/) methodology:

- **Config** — All runtime settings via environment variables (`HOST`, `PORT`, `LOG_LEVEL`, `DUCKDB_PATH`), managed by Pydantic `BaseSettings`
- **Backing Services** — DuckDB file treated as an attached resource, swappable via env var
- **Logs** — Structured JSON to stdout via `python-json-logger`, no file management
- **Port Binding** — Self-contained HTTP service via uvicorn, no external web server required
- **Disposability** — Async lifespan handler for fast startup and graceful shutdown (DuckDB connection release)
- **Observability** — Prometheus metrics at `/metrics` via `prometheus-fastapi-instrumentator`
- **Admin Processes** — CLI runs as a one-off process using the same codebase

## Development

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended for Python)

### Environment Variables

The backend reads all runtime configuration from environment variables (12-Factor: Config):

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `info` | Log level (`debug`, `info`, `warning`, `error`) |
| `DUCKDB_PATH` | `data/config.duckdb` | Path to DuckDB persistent file |

The frontend reads the backend URL at build time:

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

### Backend Setup

```bash
cd backend
uv venv
uv sync --all-extras
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Type Generation

With the backend running:

```bash
cd frontend
npm run generate-types
```

### Running the Backend

```bash
cd backend
uv run python backend/run.py
```

Or directly with uvicorn:

```bash
cd backend
uv run uvicorn backend.app.main:app --reload
```

The OpenAPI spec is served at `http://localhost:8000/openapi.json`.
Prometheus metrics are available at `http://localhost:8000/metrics`.

### Running Tests

Backend (79 tests — Hypothesis property tests + integration):

```bash
cd backend
uv run pytest tests/ -v
```

Frontend (68 tests — fast-check property tests + integration):

```bash
cd frontend
npx vitest --run
```

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/templates/packages` | GET | List available accounting packages |
| `/api/templates/packages/{pkg}/templates` | GET | List templates for a package |
| `/api/templates/packages/{pkg}/templates/{tpl}` | GET | Get full template definition |
| `/api/documentation/generate` | POST | Generate documentation artifacts |
| `/api/configurations` | GET | List saved configurations |
| `/api/configurations` | POST | Create a configuration |
| `/api/configurations/{name}` | GET/PUT/DELETE | Read/update/delete a configuration |
| `/metrics` | GET | Prometheus metrics (request count, latency, in-progress) |

### CLI

The backend includes a CLI for dev/ops use:

```bash
cd backend
uv run python -m backend.app.cli input.xlsx twinfield budget --budgetcode BC01 --year 2026
```

### Pre-commit Hooks

The repo uses [pre-commit](https://pre-commit.com/) with local hooks. Install with:

```bash
uvx pre-commit install
uvx pre-commit install --hook-type pre-push
```

On every commit:
- Ruff lint + format check on backend Python files
- TypeScript type check (`tsc --noEmit`) on frontend files
- `api.d.ts` staleness check when backend Pydantic models change

On every push:
- Full backend test suite (`pytest`)
- Full frontend test suite (`vitest`)

Run all hooks manually: `uvx pre-commit run --all-files`

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
