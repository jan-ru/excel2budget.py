# Architecture

## System Overview

The platform is split into two tiers:

- **Backend** (FastAPI + Python): Template registry, documentation generation, configuration persistence (DuckDB native), CLI
- **Frontend** (TypeScript + Vite): Excel import, DuckDB-WASM transformation, IronCalc-WASM rendering, validation, export (CSV/Excel/PDF), UI shell (@ui5/webcomponents)

The API contract flows from Pydantic models → auto-generated OpenAPI spec → openapi-typescript → TypeScript types. The financial domain model uses immutable Pydantic types (`frozen=True`) on the backend and Zod schemas on the frontend, with `FinancialDocument` as the canonical intermediate representation (fintran IR) between all readers and writers.

## Data Flow

```
User uploads .xlsx
  → Memory Guard validates size
  → Excel Importer parses client-side (SheetJS)
  → IronCalc-WASM renders preview
  → User selects package/template
  → Frontend fetches OutputTemplate from backend API
  → User sets budgetcode + year
  → Data Validator validates inputs
  → SQL Generator builds DuckDB query
  → DuckDB-WASM executes SQL in browser
  → IronCalc-WASM renders output preview
  → User exports CSV / Excel / PDF (all client-side)
  → User generates documentation
  → Frontend builds ApplicationContext (metadata only) → POST to backend
  → Backend returns DocumentationPack (7 artifacts)
```

## Data Privacy Boundary

All raw financial data (Excel cell values, transformed rows, exported files) stays in the browser. The `ApplicationContext` sent to the backend contains only metadata and aggregates — system descriptors, column descriptions, control totals, and process steps. No individual row data or cell values cross the network boundary.

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

### Financial Domain Model

The codebase uses a typed Financial Domain Model as the canonical intermediate representation (fintran IR). Key components:

- `backend/app/core/domain.py` — Immutable Pydantic models (`frozen=True`) for all financial concepts: `FinancialDocument`, `FinancialLine`, `BudgetLine`, `ActualLine`, `ForecastLine`, `Account`, `Entity`, dimension enums
- `backend/app/core/functions.py` — Pure, stateless functions for `filter_entity`, `filter_period`, `compute_variance`, `eliminate_intercompany`
- `backend/app/core/adapters.py` — Bidirectional converters between legacy `TabularData` and `FinancialDocument` for incremental migration
- `frontend/src/types/domain.ts` — Zod schemas mirroring the backend models with inferred TypeScript types

Design principles: `frozen=True` on all models (no mutation), `model_copy(update={})` for modifications, pure functions in modules (not methods), tuples for collection fields. See [`FinancialDomainModel.md`](FinancialDomainModel.md) for the full type reference.

### Control Table

Every conversion produces a reconciliation sheet proving input totals equal output totals, ensuring no data is lost or corrupted.

## Project Structure

```
├── backend/                       # FastAPI Python backend
│   ├── run.py                     # uvicorn entry point (port binding)
│   ├── app/
│   │   ├── main.py                # FastAPI entry point + lifespan handler
│   │   ├── settings.py            # Pydantic BaseSettings (env config)
│   │   ├── logging_config.py      # JSON structured logging
│   │   ├── cli.py                 # CLI entry point (dev/ops)
│   │   ├── core/
│   │   │   ├── types.py           # Pydantic models (single source of truth)
│   │   │   ├── api_models.py      # API request/response models
│   │   │   ├── domain.py          # Financial domain model (frozen Pydantic types)
│   │   │   ├── functions.py       # Pure function layer (filter, variance, eliminate)
│   │   │   └── adapters.py        # TabularData ↔ FinancialDocument converters
│   │   ├── routers/               # templates, documentation, configurations
│   │   ├── templates/             # afas, exact, twinfield definitions
│   │   ├── documentation/         # 7-artifact documentation generator
│   │   └── persistence/
│   │       └── config_store.py    # DuckDB config persistence
│   ├── tests/                     # Hypothesis property tests + integration
│   └── pyproject.toml
│
├── frontend/                      # TypeScript browser application
│   ├── src/
│   │   ├── types/
│   │   │   ├── api.d.ts           # Auto-generated from OpenAPI (DO NOT EDIT)
│   │   │   └── domain.ts          # Financial domain Zod schemas + inferred types
│   │   ├── api/client.ts          # Typed API client
│   │   ├── import/                # Excel importer (SheetJS) → produces FinancialDocument
│   │   ├── transform/             # SQL generator
│   │   ├── engine/                # DuckDB-WASM + IronCalc-WASM wrappers
│   │   ├── validation/            # Data validator
│   │   ├── security/              # XSS sanitizer
│   │   ├── guards/                # Memory guard
│   │   ├── export/                # CSV/Excel + PDF exporters ← consumes FinancialDocument
│   │   ├── pipeline/              # Orchestrator + context builder (FinancialDocument IR)
│   │   └── ui/                    # App shell, screens, components
│   ├── scripts/generate-types.ts  # OpenAPI → TypeScript type generation
│   ├── tests/                     # fast-check property tests + integration
│   └── package.json
│
├── src/                           # Original monolithic codebase (legacy)
└── docs/                          # Documentation
```


## Module Mapping: Legacy → New Architecture

| Legacy Module | New Location | Tier |
|---|---|---|
| `src/core/types.py` (dataclasses) | `backend/app/core/types.py` (Pydantic) + `frontend/src/types/api.d.ts` (generated) | Both |
| `src/core/validation.py` | `frontend/src/validation/data-validator.ts` | Frontend |
| `src/core/memory.py` | `frontend/src/guards/memory-guard.ts` | Frontend |
| `src/templates/registry.py` | `backend/app/templates/registry.py` | Backend |
| `src/templates/afas/budget.py` | `backend/app/templates/afas/budget.py` | Backend |
| `src/templates/exact/budget.py` | `backend/app/templates/exact/budget.py` | Backend |
| `src/templates/twinfield/budget.py` | `backend/app/templates/twinfield/budget.py` | Backend |
| `src/documentation/*` | `backend/app/documentation/*` | Backend |
| `src/modules/excel2budget/importer.py` | `frontend/src/import/excel-importer.ts` | Frontend |
| `src/modules/excel2budget/sql_generator.py` | `frontend/src/transform/sql-generator.ts` | Frontend |
| `src/modules/excel2budget/pipeline.py` | `frontend/src/pipeline/orchestrator.ts` | Frontend |
| `src/modules/excel2budget/context_builder.py` | `frontend/src/pipeline/context-builder.ts` | Frontend |
| `src/engine/duckdb/engine.py` | `frontend/src/engine/duckdb-engine.ts` | Frontend |
| `src/engine/ironcalc/engine.py` | `frontend/src/engine/ironcalc-engine.ts` | Frontend |
| `src/engine/ironcalc/sanitizer.py` | `frontend/src/security/xss-sanitizer.ts` | Frontend |
| `src/export/exporter.py` | `frontend/src/export/csv-excel-exporter.ts` | Frontend |
| `src/export/pdf_exporter.py` | `frontend/src/export/pdf-exporter.ts` | Frontend |
| `src/ui/app.py` | `frontend/src/ui/app.ts` + screens | Frontend |
| `src/cli.py` | `backend/app/cli.py` | Backend |
| *(new)* | `backend/app/settings.py` | Backend |
| *(new)* | `backend/app/logging_config.py` | Backend |
| *(new)* | `backend/app/core/domain.py` | Backend |
| *(new)* | `backend/app/core/functions.py` | Backend |
| *(new)* | `backend/app/core/adapters.py` | Backend |
| *(new)* | `frontend/src/types/domain.ts` | Frontend |
| *(new)* | `backend/run.py` | Backend |
