---
inclusion: always
---

# Architecture — Two-Tier Data Conversion Platform

This is the canonical architecture for the project. All code should respect these boundaries and conventions.

The full architecture is defined in #[[file:docs/architecture.md]].

## Key Rules

- Two-tier split: backend (FastAPI + Python) serves metadata, frontend (TypeScript + Vite) handles all data processing in-browser
- Raw financial data never leaves the browser — only metadata and aggregates cross the network boundary
- Frontend UI uses @ui5/webcomponents v2.7+ — no plain HTML interactive elements
- Every file creating `ui5-*` elements must have the corresponding side-effect import
- No inline CSS on UI5 elements — rely on built-in theming and `design`/`value-state` attributes
- DuckDB dual usage: native Python on backend (persistence), DuckDB-WASM in browser (SQL transforms)
- Types flow from Pydantic → OpenAPI → openapi-typescript → `api.d.ts` (single source of truth)
- `FinancialDocument` is the fintran IR — every reader produces one, every writer consumes one
- Migration order for UI changes: shared components → screens → app shell (bottom-up)
