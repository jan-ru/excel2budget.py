# Project Charter: Frontend-Backend Split

## Project Name

Data Conversion Tool — Frontend-Backend Architecture Split

## Purpose

Split the current monolithic Python data conversion tool into a two-tier architecture to achieve clear separation of concerns, enable independent deployment and testing of each tier, and enforce a strict data privacy boundary where raw financial data never leaves the user's browser.

## Problem Statement

The existing monolithic Python application bundles template management, documentation generation, configuration persistence, data import, transformation, rendering, validation, export, and the UI into a single codebase. This makes independent deployment, testing, and scaling difficult. It also lacks a clear architectural boundary for data privacy — there is no structural guarantee that sensitive financial data stays client-side.

## Project Scope

### In Scope

- Standalone FastAPI backend (Python) owning: template registry, documentation generation, customer configuration persistence (DuckDB), CLI, and the OpenAPI-based API contract
- Standalone TypeScript frontend (Vite + @ui5/webcomponents) owning: Excel import, DuckDB-WASM transformation, IronCalc-WASM spreadsheet rendering, data validation, CSV/Excel/PDF export, memory guards, pipeline orchestration, and the multi-screen UI shell
- Automated type synchronization pipeline: Pydantic → OpenAPI → openapi-typescript → TypeScript types
- Property-based testing on both tiers (Hypothesis on backend, fast-check on frontend)
- Integration tests covering the full pipeline across both tiers

### Out of Scope

- User authentication and authorization
- Multi-tenant or multi-user support
- Cloud deployment infrastructure (CI/CD pipelines, container orchestration)
- Migration of historical data or existing user configurations
- Mobile-specific UI optimizations

## Objectives

1. Establish two independently deployable and testable projects (backend + frontend)
2. Enforce a strict data privacy boundary: all raw financial data processed exclusively in the browser
3. Maintain a single source of truth for the API contract via auto-generated types
4. Preserve full CLI functionality on the backend for dev/ops use
5. Use DuckDB on both tiers (native Python for persistence, WASM for in-browser transformation) — no SQLite dependency

## Key Deliverables

| # | Deliverable | Tier |
|---|---|---|
| 1 | FastAPI backend with template registry API | Backend |
| 2 | Documentation generation API (7 artifacts) | Backend |
| 3 | Customer configuration persistence (DuckDB CRUD) | Backend |
| 4 | CLI tool (ported to Pydantic types) | Backend |
| 5 | OpenAPI spec auto-generated from Pydantic models | Backend |
| 6 | Type generation pipeline (openapi-typescript) | Both |
| 7 | Client-side Excel importer (SheetJS) | Frontend |
| 8 | Client-side SQL generation and DuckDB-WASM transformation | Frontend |
| 9 | Data validation module | Frontend |
| 10 | IronCalc-WASM spreadsheet rendering with XSS sanitization | Frontend |
| 11 | CSV, Excel, and PDF export (all client-side) | Frontend |
| 12 | Memory and WASM guards | Frontend |
| 13 | Pipeline orchestrator (import → validate → transform → preview → export) | Frontend |
| 14 | Multi-screen UI shell (Upload, Preview, Configuration, Transform, Output, Documentation) | Frontend |
| 15 | Property-based test suites (Hypothesis + fast-check) | Both |
| 16 | Integration test suite | Both |

## Stakeholders

| Role | Responsibility |
|---|---|
| Developer(s) | Implementation, testing, code review |
| End Users | Upload Excel budget files, configure templates, transform data, export results, generate documentation |
| Ops / DevOps | Backend deployment, CLI usage, configuration management |

## Technical Decisions

| Decision | Rationale |
|---|---|
| FastAPI + Pydantic (backend) | Auto-generates OpenAPI spec from type definitions; strong typing |
| Plain TypeScript + Vite (frontend) | No framework overhead; lightweight, fast builds |
| @ui5/webcomponents for UI | Framework-agnostic SAP web components; no full UI5 dependency |
| DuckDB on both tiers | Native Python for persistence, WASM for browser transformation; avoids SQLite dependency |
| IronCalc-WASM for rendering | In-browser spreadsheet preview without server round-trips |
| openapi-typescript for type sync | Single source of truth; eliminates manual type duplication |
| jsPDF / pdf-lib for PDF export | Fully client-side; no server involvement for exports |
| Hypothesis + fast-check for PBT | Property-based testing on both tiers for formal correctness guarantees |

## Constraints

- The frontend must not use React, Vue, Angular, or the full SAP UI5 framework
- The frontend must be fully ephemeral — no localStorage, IndexedDB, or server transmission of financial data
- The backend must not use SQLite or any database other than DuckDB
- All raw financial data processing must happen exclusively in the browser
- The ApplicationContext sent to the backend for documentation must contain only metadata and aggregates

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| DuckDB-WASM or IronCalc-WASM browser compatibility issues | Users on older browsers may not be able to use the tool | Document minimum browser requirements; test across major browsers |
| Large Excel files exceeding WASM memory limits | Browser tab crashes | Memory_Guard validates file size and estimated footprint before parsing |
| OpenAPI type generation drift | Frontend/backend type mismatch causing runtime errors | Type generation is a single CLI command; run as part of build process |
| SheetJS (xlsx) licensing changes | Dependency risk for Excel parsing | Monitor upstream; evaluate ExcelJS as fallback |

## Success Criteria

- All 18 requirements pass acceptance criteria
- All property-based tests pass (minimum 100 iterations each)
- Integration tests cover the full pipeline (upload → transform → export) and documentation generation
- No raw financial data is transmitted from the browser to any server (verified by audit)
- Backend and frontend can be built, tested, and deployed independently
- CLI preserves all existing command-line functionality
