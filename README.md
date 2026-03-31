# Data Conversion Tool

A two-tier data conversion platform that transforms financial data between source formats and accounting package import formats. The frontend runs entirely in the browser via WebAssembly ([IronCalc](https://www.ironcalc.com/) for spreadsheet rendering, [DuckDB WASM](https://duckdb.org/docs/api/wasm/overview) for SQL transformations). The backend ([FastAPI](https://fastapi.tiangolo.com/)) serves template definitions, documentation generation, and configuration persistence. Raw financial data never leaves the browser.

## Overview

This tool is part of a larger system of application modules, each handling a specific conversion use case:

| Module | Purpose |
|---|---|
| **excel2budget** | Convert Excel budget files (wide month columns) into accounting package budget import formats |
| **update_forecast** | Update forecast data in accounting packages *(planned)* |
| **reporting_actuals** | Report actuals data from accounting packages *(planned)* |

Supported accounting packages: Twinfield (full), Exact (stub), Afas (stub).

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

All raw financial data stays in the browser. Only metadata and aggregates are sent to the backend for documentation generation. See [Architecture](docs/architecture.md) for details.

## Quick Start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+

### Setup

```bash
# Backend
cd backend && uv venv && uv sync --all-extras

# Frontend
cd frontend && npm install
```

### Run

```bash
# Backend
cd backend && uv run uvicorn backend.app.main:app --reload

# Frontend
cd frontend && npm run dev
```

### Test

```bash
# Backend (115 tests)
cd backend && uv run pytest tests/ -v

# Frontend (170 tests)
cd frontend && npx vitest --run
```

## Financial Domain Model

The codebase uses a typed Financial Domain Model defined in [`FinancialDomainModel.md`](docs/FinancialDomainModel.md) as the canonical intermediate representation (fintran IR). The model is fully implemented:

- Immutable Pydantic types (`frozen=True`) in `backend/app/core/domain.py` and Zod schemas in `frontend/src/types/domain.ts`
- `FinancialDocument` as the fintran IR — every reader produces one, every writer consumes one
- Pure functions (`filter_entity`, `filter_period`, `compute_variance`, `eliminate_intercompany`) in `backend/app/core/functions.py`
- Adapter layer (`TabularData ↔ FinancialDocument`) in `backend/app/core/adapters.py` for incremental migration
- Frontend pipeline (import → orchestrator → export) fully migrated to `FinancialDocument`

See the [spec](.kiro/specs/financial-domain-model/) for requirements, design, and implementation plan.

## Recent Changes

- **UI5 Web Components Migration**: Migrated the entire frontend from plain HTML elements with inline CSS to UI5 Web Components v2.7+. Navigation uses `ui5-tabcontainer`, forms use `ui5-select`/`ui5-input`/`ui5-label`, buttons use `ui5-button`, file upload uses `ui5-file-uploader`, and error banners use `ui5-message-strip`. All inline styles removed from UI5 elements in favor of built-in theming. 10 property-based tests validate correctness properties (import discipline, no inline styles, component structure, validation states, accessibility pairing).
- **Financial Domain Model**: Implemented the full typed domain model — immutable Pydantic types (backend), Zod schemas (frontend), pure function layer, adapter layer, and frontend pipeline migration to `FinancialDocument` IR. 17 property-based tests validate correctness properties across the stack.
- **Header Row Selection**: Auto-detects or prompts for the header row when importing Excel files with preamble rows above the actual column headers. Progressive summary shows filename, sheet, and header row as each step resolves.
- **IronCalc WASM fix**: Fixed WebAssembly loading in Vite dev mode by excluding `@ironcalc/wasm` from dependency pre-bundling.
- **DuckDB WASM fix**: Switched to Vite `?url` imports for reliable WASM asset resolution in both dev and production.
- **PDF export fix**: Fixed corrupt PDF downloads caused by incorrect `ArrayBuffer` → `Uint8Array` handling, and added actual grid data to PDF content.
- **CORS**: Added CORS middleware to the FastAPI backend for cross-origin requests from the Vite dev server.
- **Number formatting**: Amount columns (col 5+) now display with 2 decimal places and right alignment in the IronCalc preview.

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System design, data flow, module mapping, key concepts |
| [Configuration](docs/configuration.md) | Environment variables, 12-factor compliance, build/release/run |
| [API Reference](docs/api.md) | REST endpoints, error handling, OpenAPI spec, metrics |
| [Development Guide](docs/development.md) | Full setup, type generation, testing, CLI, pre-commit hooks |
| [Deployment](docs/deployment.md) | Docker setup, Coolify/Hetzner deployment, production notes |
| [Financial Domain Model](docs/FinancialDomainModel.md) | Typed domain model reference — Pydantic types, Zod schemas, pure functions |

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
