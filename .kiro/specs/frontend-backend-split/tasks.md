# Implementation Plan: Frontend-Backend Split

## Overview

Split the monolithic Python data conversion tool into a FastAPI backend (Python) and a plain TypeScript frontend (Vite + @ui5/webcomponents). Backend owns templates, documentation, config persistence (DuckDB), and CLI. Frontend owns all data processing: Excel import, DuckDB-WASM transformation, IronCalc-WASM rendering, validation, export, and the UI shell. Types flow from Pydantic → OpenAPI → openapi-typescript.

## Tasks

- [x] 1. Backend project scaffolding and core Pydantic types
  - [x] 1.1 Create backend project structure with pyproject.toml, FastAPI dependency, and directory layout (`backend/app/`, `backend/app/core/`, `backend/app/routers/`, `backend/app/templates/`, `backend/app/documentation/`, `backend/app/persistence/`, `backend/tests/`)
    - Initialize `backend/pyproject.toml` with FastAPI, Pydantic, DuckDB, uvicorn, Hypothesis, pytest, httpx dependencies
    - Create `__init__.py` files for all packages
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Convert all dataclass types in `src/core/types.py` to Pydantic BaseModel subclasses in `backend/app/core/types.py`
    - Convert enums to `str, Enum` subclasses for JSON serialization
    - Convert CellValue and ColumnSourceMapping unions to Pydantic discriminated unions with `type` literal discriminator fields
    - Convert all dataclasses (ColumnDef, Row, DataMetadata, TabularData, MappingConfig, UserParams, MonthColumnDef, OutputTemplate, TemplateColumnDef, ValidationResult, all documentation types, PDFMetadata, etc.) to BaseModel subclasses
    - _Requirements: 1.3_

  - [x] 1.3 Create API request/response models in `backend/app/core/api_models.py`
    - Define PackageListResponse, TemplateListResponse, OutputTemplateResponse, ErrorResponse, CreateConfigurationRequest, UpdateConfigurationRequest, CustomerConfiguration, ConfigurationListResponse
    - _Requirements: 17.1, 17.4_

  - [x] 1.4 Create FastAPI app entry point in `backend/app/main.py`
    - Mount template, documentation, and configuration routers
    - Ensure OpenAPI spec is auto-generated and served at `/openapi.json`
    - _Requirements: 1.4, 1.5_

  - [x] 1.5 Write property test: Type Pipeline Round-Trip (Property 1)
    - **Property 1: Type Pipeline Round-Trip**
    - Verify that every Pydantic model in `backend/app/core/types.py` appears in the generated OpenAPI spec with matching fields
    - **Validates: Requirements 3.1**


- [x] 2. Backend Template Registry API
  - [x] 2.1 Port template definitions (afas, exact, twinfield) to `backend/app/templates/` using Pydantic types
    - Port `src/templates/registry.py` to `backend/app/templates/registry.py`
    - Port `src/templates/afas/budget.py`, `src/templates/exact/budget.py`, `src/templates/twinfield/budget.py` to use Pydantic OutputTemplate
    - _Requirements: 4.5_

  - [x] 2.2 Implement template registry router in `backend/app/routers/templates.py`
    - GET `/api/templates/packages` → PackageListResponse
    - GET `/api/templates/packages/{package}/templates` → TemplateListResponse
    - GET `/api/templates/packages/{package}/templates/{template}` → OutputTemplateResponse
    - Return ErrorResponse with available packages/templates on 404
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 2.3 Write property test: Template Registry API Round-Trip (Property 2)
    - **Property 2: Template Registry API Round-Trip**
    - For any registered package/template, list-packages includes the package, list-templates includes the template, get-template returns matching OutputTemplate
    - Use Hypothesis + httpx TestClient
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 2.4 Write property test: Template API Error on Invalid Lookup (Property 3)
    - **Property 3: Template API Error on Invalid Lookup**
    - For any non-existent package, the API returns error with available packages; for valid package but non-existent template, returns error with available templates
    - **Validates: Requirements 4.4**

- [x] 3. Backend Configuration Persistence (DuckDB)
  - [x] 3.1 Implement ConfigStore in `backend/app/persistence/config_store.py`
    - Create DuckDB persistent file at configurable path
    - Implement `_ensure_schema()` to create `customer_configurations` table if not exists
    - Implement CRUD methods: create, get, list_all, update, delete
    - Store: name, package_name, template_name, budgetcode, year, created_at, updated_at
    - _Requirements: 6.1, 6.3, 16.1, 16.3_

  - [x] 3.2 Implement configuration router in `backend/app/routers/configurations.py`
    - GET `/api/configurations` → ConfigurationListResponse
    - POST `/api/configurations` → ConfigurationResponse (201)
    - GET `/api/configurations/{name}` → ConfigurationResponse or 404
    - PUT `/api/configurations/{name}` → ConfigurationResponse or 404
    - DELETE `/api/configurations/{name}` → 204 or 404
    - _Requirements: 6.2, 6.4_

  - [x] 3.3 Write property test: Configuration CRUD Round-Trip (Property 5)
    - **Property 5: Configuration CRUD Round-Trip**
    - For any valid configuration, create → get returns matching fields with non-null timestamps
    - Use Hypothesis + httpx TestClient
    - **Validates: Requirements 6.2, 6.3, 6.4**

- [-] 4. Backend Documentation Generation API
  - [x] 4.1 Port documentation module to `backend/app/documentation/`
    - Port `src/documentation/module.py`, `control_table.py`, `description_generator.py`, `diagram_generator.py`, `user_instruction.py` to use Pydantic types
    - _Requirements: 5.3_

  - [x] 4.2 Implement documentation router in `backend/app/routers/documentation.py`
    - POST `/api/documentation/generate` accepts ApplicationContext, returns DocumentationPack
    - Return 400 with descriptive error for incomplete/invalid ApplicationContext
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 4.3 Write property test: Documentation Generation Completeness (Property 4)
    - **Property 4: Documentation Generation Completeness**
    - For any valid ApplicationContext with all required fields, the response contains all 7 non-null artifacts
    - **Validates: Requirements 5.1, 5.3**

- [x] 5. Backend CLI Port
  - [x] 5.1 Port CLI to `backend/app/cli.py` using Pydantic types and backend template registry
    - Port `src/cli.py` to use Pydantic-based core types
    - Use backend template registry (same as API_Gateway)
    - Preserve all existing arguments: positional (input_file, package, template), required flags (--budgetcode, --year), optional flags (-o, -f, -v, -q, --list-packages, --list-templates, --version)
    - Exit codes: 0 success, 1 input/config errors, 2 transform/export errors
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 5.2 Write property test: CLI Argument Parsing and Exit Codes (Property 17)
    - **Property 17: CLI Argument Parsing and Exit Codes**
    - Valid invocations are accepted; exit code 0 on success, 1 on input errors, 2 on transform errors
    - **Validates: Requirements 15.1, 15.3**


- [x] 6. Backend checkpoint and API contract validation
  - [x] 6.1 Write property test: API Response Consistency (Property 18)
    - **Property 18: API Response Consistency**
    - For any API endpoint call, response is valid JSON; success → 200, client error → 400/422, not found → 404; all error responses have non-empty `detail`
    - **Validates: Requirements 17.1, 17.2, 17.3**

  - [x] 6.2 Checkpoint — Ensure all backend tests pass
    - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend project scaffolding and type generation pipeline
  - [x] 7.1 Create frontend project structure with package.json, tsconfig.json, vite.config.ts, index.html
    - Initialize `frontend/` with Vite + TypeScript template
    - Add dependencies: @ui5/webcomponents, @duckdb/duckdb-wasm, fast-check, vitest, jspdf (or pdf-lib), sheetjs (xlsx)
    - Create directory layout: `frontend/src/types/`, `frontend/src/api/`, `frontend/src/import/`, `frontend/src/transform/`, `frontend/src/engine/`, `frontend/src/validation/`, `frontend/src/security/`, `frontend/src/export/`, `frontend/src/guards/`, `frontend/src/pipeline/`, `frontend/src/ui/`, `frontend/src/ui/screens/`, `frontend/src/ui/components/`
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 7.2 Implement type generation script in `frontend/scripts/generate-types.ts`
    - Use openapi-typescript to fetch OpenAPI spec from backend and generate `frontend/src/types/api.d.ts`
    - Add `generate-types` npm script to package.json
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 7.3 Run type generation and commit initial `frontend/src/types/api.d.ts`
    - Execute `npm run generate-types` against running backend to produce the initial generated types file
    - Verify generated types contain interfaces for OutputTemplate, ApplicationContext, DocumentationPack, CustomerConfiguration, etc.
    - _Requirements: 3.3, 3.5_

- [x] 8. Frontend API client
  - [x] 8.1 Implement typed API client in `frontend/src/api/client.ts`
    - Use `fetch` with generated TypeScript types
    - Implement: getPackages, getTemplates, getTemplate, generateDocumentation, listConfigurations, getConfiguration, createConfiguration, updateConfiguration, deleteConfiguration
    - Wrap all calls in Result<T> type for consistent error handling
    - Configure BASE_URL from `import.meta.env.VITE_API_URL`
    - _Requirements: 13.2, 14.3, 17.1_

- [x] 9. Frontend Memory Guard
  - [x] 9.1 Implement Memory_Guard in `frontend/src/guards/memory-guard.ts`
    - Port `src/core/memory.py` to TypeScript
    - Validate file size against configurable maximum
    - Estimate in-memory footprint (file size × expansion factor) vs WASM limit
    - Reject with descriptive error if either limit exceeded
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 9.2 Write property test: Memory Guard Rejection (Property 15)
    - **Property 15: Memory Guard Rejection**
    - Files exceeding max size are rejected; files where size × factor exceeds WASM limit are rejected; files within both limits are accepted
    - Use fast-check with `fc.assert(property, { numRuns: 100 })`
    - **Validates: Requirements 12.1, 12.2, 12.3**

- [x] 10. Frontend Excel Importer
  - [x] 10.1 Implement Excel_Importer in `frontend/src/import/excel-importer.ts`
    - Port `src/modules/excel2budget/importer.py` to TypeScript using SheetJS (xlsx)
    - Parse .xlsx client-side, extract budget data from "Budget" sheet
    - Extract column mapping config (Entity, Account, DC, Dutch month columns)
    - Return descriptive errors for invalid files or missing sheets
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 10.2 Write property test: Month Column Detection from Headers (Property 6)
    - **Property 6: Month Column Detection from Headers**
    - For any header list with Entity, Account, DC, and Dutch month-pattern columns, the extractor identifies all month columns with correct period numbers and years
    - Use fast-check
    - **Validates: Requirements 7.3**

  - [x] 10.3 Write property test: Invalid File Error Handling (Property 7)
    - **Property 7: Invalid File Error Handling**
    - For any byte sequence that is not a valid .xlsx, the importer returns a descriptive non-empty error
    - Use fast-check
    - **Validates: Requirements 7.4**


- [x] 11. Frontend Data Validator
  - [x] 11.1 Implement Data_Validator in `frontend/src/validation/data-validator.ts`
    - Port `src/core/validation.py` to TypeScript
    - Validate MappingConfig column references exist in imported data
    - Validate UserParams (non-empty budgetcode, positive year)
    - Detect invalid DC values (not "D", "C", or null) with row-level detail
    - Validate month column period numbers unique and in range 1–12
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 11.2 Write property test: MappingConfig Validation (Property 9)
    - **Property 9: MappingConfig Validation**
    - Reports error if any referenced column is missing, period numbers outside 1–12, or duplicate period numbers
    - Use fast-check
    - **Validates: Requirements 9.1, 9.4**

  - [x] 11.3 Write property test: UserParams Validation (Property 10)
    - **Property 10: UserParams Validation**
    - Reports failure for empty budgetcode or non-positive year
    - Use fast-check
    - **Validates: Requirements 9.2**

  - [x] 11.4 Write property test: DC Value Validation (Property 11)
    - **Property 11: DC Value Validation**
    - Detects and reports every row with invalid DC value (not "D", "C", or null), including row index and value
    - Use fast-check
    - **Validates: Requirements 9.3**

- [x] 12. Frontend SQL Generator
  - [x] 12.1 Implement SQL_Generator in `frontend/src/transform/sql-generator.ts`
    - Port `src/modules/excel2budget/sql_generator.py` to TypeScript
    - Generate DuckDB-compatible SELECT-only SQL for unpivot + DC split
    - Use quoted identifiers to prevent SQL injection
    - Handle FromSource, FromUserParam, FromTransform, FixedNull column source mappings
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 12.2 Write property test: SQL Generation Safety (Property 8)
    - **Property 8: SQL Generation Safety**
    - For any valid MappingConfig, OutputTemplate, and UserParams, the generated SQL starts with WITH/SELECT (no DDL/DML), uses quoted identifiers, handles special characters
    - Use fast-check
    - **Validates: Requirements 8.1, 8.2, 8.4**

- [x] 13. Frontend XSS Sanitizer
  - [x] 13.1 Implement XSS_Sanitizer in `frontend/src/security/xss-sanitizer.ts`
    - Port `src/engine/ironcalc/sanitizer.py` to TypeScript
    - Strip HTML tags, script elements, event handler attributes, dangerous URI schemes (javascript:, vbscript:, data:)
    - HTML-entity-encode remaining angle brackets and ampersands
    - _Requirements: 10.2, 10.3_

  - [x] 13.2 Write property test: XSS Sanitization (Property 12)
    - **Property 12: XSS Sanitization**
    - Output contains no HTML tags, javascript: URIs, vbscript: URIs, on-event attributes, or script elements
    - Use fast-check
    - **Validates: Requirements 10.2, 10.3**

- [x] 14. Checkpoint — Ensure all frontend module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Frontend DuckDB-WASM Engine
  - [x] 15.1 Implement DuckDB_WASM engine wrapper in `frontend/src/engine/duckdb-engine.ts`
    - Wrap @duckdb/duckdb-wasm for in-browser SQL execution
    - Implement: initialize, registerTable (from TabularData), executeSql (returns TabularData), close
    - _Requirements: 8.3, 16.2_

- [x] 16. Frontend IronCalc-WASM Engine
  - [x] 16.1 Implement IronCalc_WASM engine wrapper in `frontend/src/engine/ironcalc-engine.ts`
    - Wrap IronCalc WASM for spreadsheet rendering
    - Implement: loadData (from TabularData), renderToElement (mount spreadsheet view into DOM element)
    - Sanitize all cell values via XSS_Sanitizer before rendering
    - _Requirements: 10.1, 10.2_

- [x] 17. Frontend Exporters
  - [x] 17.1 Implement CSV_Excel_Exporter in `frontend/src/export/csv-excel-exporter.ts`
    - CSV export via string building, trigger browser download
    - Excel export via SheetJS (xlsx), trigger browser download
    - No server transmission of exported data
    - _Requirements: 11.1, 11.2, 11.5_

  - [x] 17.2 Write property test: CSV/Excel Export Round-Trip (Property 13)
    - **Property 13: CSV/Excel Export Round-Trip**
    - For any valid TabularData, export to CSV and parse back preserves column names, row count, and string representations
    - Use fast-check
    - **Validates: Requirements 11.1, 11.2**

  - [x] 17.3 Implement PDF_Exporter in `frontend/src/export/pdf-exporter.ts`
    - Client-side PDF generation using jsPDF or pdf-lib
    - Include metadata: screen title, configuration name, package, template, generation timestamp
    - Support screen content types: spreadsheet, diagram, control table
    - _Requirements: 11.3, 11.4_

  - [x] 17.4 Write property test: PDF Generation with Metadata (Property 14)
    - **Property 14: PDF Generation with Metadata**
    - Output is non-empty bytes starting with `%PDF`; content contains screenTitle, configurationName, packageName, templateName
    - Use fast-check
    - **Validates: Requirements 11.3, 11.4**


- [x] 18. Frontend Pipeline Orchestrator and Context Builder
  - [x] 18.1 Implement Pipeline_Orchestrator in `frontend/src/pipeline/orchestrator.ts`
    - Coordinate: file import → Memory_Guard → Excel_Importer → Data_Validator → API_Client.getTemplate → SQL_Generator → DuckDB_WASM.execute → result preview
    - Hold session state in-memory (ephemeral, no persistence)
    - Halt on first error, return descriptive error to caller
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 2.4, 2.5_

  - [x] 18.2 Implement context builder in `frontend/src/pipeline/context-builder.ts`
    - Port `src/modules/excel2budget/context_builder.py` to TypeScript
    - Build ApplicationContext from session data (metadata and aggregates only, no raw financial data)
    - Compute control totals for reconciliation
    - _Requirements: 5.2, 18.3_

  - [x] 18.3 Write property test: Pipeline Halt on Failure (Property 16)
    - **Property 16: Pipeline Halt on Failure**
    - If step N fails, no step after N executes, and the pipeline returns an error describing the failure at step N
    - Use fast-check
    - **Validates: Requirements 13.3**

- [x] 19. Frontend UI Application Shell
  - [x] 19.1 Implement app shell and screen router in `frontend/src/ui/app.ts`
    - Screen-based navigation: Upload, Preview, Configuration, Transform, Output, Documentation
    - Use plain TypeScript + @ui5/webcomponents
    - _Requirements: 14.1_

  - [x] 19.2 Implement shared UI components
    - `frontend/src/ui/components/header.ts`: current date display (YYYY-MM-DD) + "Download as PDF" action
    - `frontend/src/ui/components/error-banner.ts`: error display component
    - _Requirements: 14.2_

  - [x] 19.3 Implement Upload screen in `frontend/src/ui/screens/upload.ts`
    - File input accepting .xlsx, triggers Pipeline_Orchestrator.importFile
    - Show error banner on failure
    - _Requirements: 7.1, 14.1_

  - [x] 19.4 Implement Preview screen in `frontend/src/ui/screens/preview.ts`
    - Display imported data summary (row count, column count)
    - Render IronCalc spreadsheet preview of source data
    - _Requirements: 10.1, 14.1_

  - [x] 19.5 Implement Configuration screen in `frontend/src/ui/screens/configuration.ts`
    - Fetch and display available packages/templates from backend API
    - Template selection dropdowns and user parameter inputs (budgetcode, year)
    - _Requirements: 14.1, 14.3_

  - [x] 19.6 Implement Transform screen in `frontend/src/ui/screens/transform.ts`
    - Trigger transformation via Pipeline_Orchestrator.runTransform
    - Display success/error result
    - _Requirements: 8.3, 14.1_

  - [x] 19.7 Implement Output screen in `frontend/src/ui/screens/output.ts`
    - Display transformed data in IronCalc spreadsheet preview
    - Export buttons for CSV, Excel, PDF
    - _Requirements: 10.1, 11.1, 11.2, 11.3, 14.1_

  - [x] 19.8 Implement Documentation screen in `frontend/src/ui/screens/documentation.ts`
    - Build ApplicationContext and send to backend documentation endpoint
    - Display all 7 documentation artifacts
    - _Requirements: 5.1, 14.1, 14.4_

- [x] 20. Frontend data privacy enforcement
  - [x] 20.1 Verify data privacy boundary across all frontend modules
    - Audit that no module transmits raw financial data (cell values, rows, exported files) to any server
    - Verify ApplicationContext contains only metadata/aggregates
    - Ensure all data processing is in-memory and ephemeral
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 2.4, 2.5_

- [x] 21. Integration testing
  - [x] 21.1 Write integration tests for full pipeline flow
    - Upload → validate → fetch template from backend → transform → export (frontend + backend running)
    - Documentation generation: build ApplicationContext → POST to backend → verify 7 artifacts returned
    - Configuration persistence: create → list → update → get → delete cycle
    - _Requirements: 13.1, 5.1, 6.2_

- [x] 22. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Backend uses Python (FastAPI + Pydantic + Hypothesis for property tests)
- Frontend uses TypeScript (Vite + @ui5/webcomponents + fast-check for property tests)
- Each task references specific requirements for traceability
- Checkpoints at task 6 (backend complete), task 14 (frontend modules), and task 22 (final)
- Property tests validate universal correctness properties from the design document
- Type generation pipeline (task 7) bridges backend Pydantic models to frontend TypeScript types
