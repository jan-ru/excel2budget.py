# Requirements Document

## Introduction

This document specifies the requirements for refactoring the fintran codebase from its current generic `TabularData` / `ColumnDef` / `Row` model to the Financial Domain Model defined in `FinancialDomainModel.md`. The refactoring introduces typed Pydantic models (Python backend) and Zod schemas (TypeScript frontend), establishes `FinancialDocument` as the canonical intermediate representation (fintran IR), and adds a pure function layer for financial computations. All existing import/export flows must continue to work throughout the migration.

## Glossary

- **Domain_Model**: The set of typed financial models defined in `FinancialDomainModel.md`, including primitive types, dimension models, line types, statement lines, and `FinancialDocument`.
- **Backend**: The Python FastAPI application in `backend/app/`.
- **Frontend**: The TypeScript browser application in `frontend/src/`.
- **FinancialDocument**: The top-level immutable Pydantic model serving as the fintran IR. Contains `lines`, `accounts`, `entities`, and `meta`. Every reader produces one; every writer consumes one.
- **FinancialLine**: The core immutable model representing a single financial line with `account`, `entity`, `period`, `amount`, `line_type`, `currency`, and `memo`.
- **BudgetLine**: A specialised `FinancialLine` with `line_type` locked to `"budget"` and an additional `version` field.
- **ActualLine**: A specialised `FinancialLine` with `line_type` locked to `"actual"` and an optional `journal_ref` field.
- **ForecastLine**: A specialised `FinancialLine` with `line_type` locked to `"forecast"` and a `basis` field.
- **Account**: An immutable dimension model with `code`, `description`, `account_type`, `normal_balance`, and optional `parent_code`.
- **Entity**: An immutable dimension model with `code`, `description`, and `is_elimination` flag.
- **Period**: An immutable dimension model with `value`, `year`, `month`, and `fiscal_year`.
- **IncomeStatementLine**: A computed (never stored) immutable model containing `budget`, `actual`, `forecast`, `variance_bva`, and `variance_bvf` for a given account/entity/period.
- **BalanceSheetLine**: A computed immutable model with `balance` and `line_type` for a given account/entity/period.
- **CashflowLine**: A computed immutable model with `inflow`, `outflow`, `net`, and `line_type` for a given account/entity/period.
- **LineType**: A string enum with values `"budget"`, `"actual"`, `"forecast"`.
- **AccountType**: A string enum with values `"asset"`, `"liability"`, `"equity"`, `"revenue"`, `"expense"`.
- **DebitCredit**: A string enum with values `"D"`, `"C"`.
- **AccountCode**: A NewType string wrapper for account codes (e.g. `"4001"`).
- **EntityCode**: A NewType string wrapper for entity codes (e.g. `"MS"`, `"MH"`, `"EL"`).
- **Pure_Function_Layer**: A set of stateless, side-effect-free functions operating on `FinancialDocument` for filtering, variance computation, and intercompany elimination.
- **TabularData**: The current generic internal representation using `ColumnDef`, `Row`, and `CellValue` — to be replaced by `FinancialDocument`.
- **Zod**: A TypeScript schema validation library used to define and validate frontend domain types.
- **Reader**: Any module that ingests external data (Excel files, CSV, API responses) and produces a `FinancialDocument`.
- **Writer**: Any module that consumes a `FinancialDocument` and produces external output (CSV, Excel, accounting package import files).

## Requirements

### Requirement 1: Backend Domain Model Types

**User Story:** As a backend developer, I want typed, immutable Pydantic models for all financial domain concepts, so that the codebase enforces domain correctness at the type level and prevents accidental mutation.

#### Acceptance Criteria

1. THE Backend SHALL define `AccountCode`, `EntityCode`, and `Period` as `NewType` string wrappers in a dedicated `backend/app/core/domain.py` module.
2. THE Backend SHALL define `LineType`, `AccountType`, and `DebitCredit` as `StrEnum` classes with the values specified in the Domain_Model.
3. THE Backend SHALL define `Account`, `Entity`, and `Period` as Pydantic `BaseModel` subclasses with `frozen=True`, containing the fields specified in the Domain_Model.
4. THE Backend SHALL define `FinancialLine` as a Pydantic `BaseModel` subclass with `frozen=True`, containing `account` (AccountCode), `entity` (EntityCode), `period` (str), `amount` (Decimal), `line_type` (LineType), `currency` (str, default "EUR"), and `memo` (str | None, default None).
5. THE Backend SHALL define `BudgetLine`, `ActualLine`, and `ForecastLine` as subclasses of `FinancialLine` with `frozen=True`, each locking `line_type` via `Literal` and adding their specialised fields as specified in the Domain_Model.
6. THE Backend SHALL define `IncomeStatementLine`, `BalanceSheetLine`, and `CashflowLine` as Pydantic `BaseModel` subclasses with `frozen=True`, containing the fields specified in the Domain_Model.
7. THE Backend SHALL define `FinancialDocument` as a Pydantic `BaseModel` subclass with `frozen=True`, containing `lines` (tuple of FinancialLine), `accounts` (tuple of Account), `entities` (tuple of Entity), and `meta` (dict of str to str).
8. WHEN any code attempts to assign a field on a frozen domain model instance, THE Backend SHALL raise a `ValidationError` (Pydantic's standard frozen-field error).

### Requirement 2: Frontend Domain Model Types

**User Story:** As a frontend developer, I want typed Zod schemas mirroring the backend domain models, so that the frontend validates and consumes financial data with the same type safety as the backend.

#### Acceptance Criteria

1. THE Frontend SHALL define Zod schemas for `AccountCode`, `EntityCode`, `LineType`, `AccountType`, and `DebitCredit` in a dedicated `frontend/src/types/domain.ts` module.
2. THE Frontend SHALL define Zod schemas for `Account`, `Entity`, `FinancialLine`, `BudgetLine`, `ActualLine`, `ForecastLine`, `IncomeStatementLine`, `BalanceSheetLine`, `CashflowLine`, and `FinancialDocument` matching the field names and types of the corresponding Backend models.
3. THE Frontend SHALL export inferred TypeScript types from each Zod schema using `z.infer<>`.
4. WHEN the Frontend receives a JSON payload representing a `FinancialDocument`, THE Frontend SHALL validate the payload against the `FinancialDocument` Zod schema before use.
5. IF the Zod validation fails, THEN THE Frontend SHALL surface a descriptive error message identifying the invalid field and expected type.

### Requirement 3: FinancialDocument as Fintran IR

**User Story:** As a system architect, I want `FinancialDocument` to serve as the single intermediate representation between all readers and writers, so that the pipeline has a well-defined, typed contract at every boundary.

#### Acceptance Criteria

1. WHEN an Excel budget file is imported, THE Reader SHALL produce a `FinancialDocument` containing one `BudgetLine` per data cell (account × entity × period), the detected `Account` dimension entries, the detected `Entity` dimension entries, and metadata including the source filename and import timestamp.
2. WHEN a `FinancialDocument` is exported to CSV, THE Writer SHALL consume the `FinancialDocument` and produce a CSV file with one row per `FinancialLine`, using column headers derived from the output template.
3. WHEN a `FinancialDocument` is exported to Excel, THE Writer SHALL consume the `FinancialDocument` and produce an `.xlsx` file with one row per `FinancialLine`, using column headers derived from the output template.
4. THE Backend SHALL not pass `TabularData` between pipeline stages; all inter-stage data transfer SHALL use `FinancialDocument`.
5. THE Frontend SHALL not pass `TabularData` between pipeline stages; all inter-stage data transfer SHALL use `FinancialDocument` or its Zod-validated TypeScript equivalent.

### Requirement 4: Backend Reader Refactoring

**User Story:** As a backend developer, I want every data reader to produce a `FinancialDocument`, so that downstream processing always receives typed, validated financial data.

#### Acceptance Criteria

1. WHEN the Excel budget reader parses a valid workbook, THE Reader SHALL return a `FinancialDocument` with `lines` containing `BudgetLine` instances, `accounts` containing `Account` instances extracted from the account column, `entities` containing `Entity` instances extracted from the entity column, and `meta` containing at minimum `{"source": <filename>}`.
2. WHEN the Excel budget reader encounters a row with a missing or empty account code, THE Reader SHALL skip the row and record a warning in the `meta` dictionary under the key `"warnings"`.
3. WHEN the Excel budget reader encounters a non-numeric value in a month column, THE Reader SHALL treat the value as `Decimal("0")` and record a warning in `meta`.
4. IF the Excel budget reader receives an empty or unreadable file, THEN THE Reader SHALL raise a descriptive error without producing a partial `FinancialDocument`.

### Requirement 5: Backend Writer Refactoring

**User Story:** As a backend developer, I want every data writer to consume a `FinancialDocument`, so that export logic operates on typed domain data rather than generic tabular structures.

#### Acceptance Criteria

1. WHEN the CSV writer receives a `FinancialDocument` and an `OutputTemplate`, THE Writer SHALL produce a CSV string with columns matching the template column definitions and one row per `FinancialLine`.
2. WHEN the Excel writer receives a `FinancialDocument` and an `OutputTemplate`, THE Writer SHALL produce an `.xlsx` byte buffer with columns matching the template column definitions and one row per `FinancialLine`.
3. WHEN a `FinancialLine` field maps to a template column via `from_source`, THE Writer SHALL extract the corresponding field value from the `FinancialLine`.
4. WHEN a template column uses `from_transform` with expression `"period_number"`, THE Writer SHALL extract the period number from the `FinancialLine.period` field.
5. WHEN a template column uses `from_transform` with a DC-based expression, THE Writer SHALL split the `FinancialLine.amount` into debit and credit columns based on the account's `normal_balance` from the `Account` dimension in the `FinancialDocument`.

### Requirement 6: Pure Function Layer

**User Story:** As a developer, I want a set of pure, stateless functions for filtering, variance computation, and intercompany elimination, so that financial logic is testable, composable, and free of side effects.

#### Acceptance Criteria

1. THE Pure_Function_Layer SHALL provide a `filter_entity` function that accepts a `FinancialDocument` and an `EntityCode` and returns a new `FinancialDocument` containing only lines matching the specified entity.
2. THE Pure_Function_Layer SHALL provide a `filter_period` function that accepts a `FinancialDocument` and a year (int) and returns a new `FinancialDocument` containing only lines whose period starts with the specified year.
3. THE Pure_Function_Layer SHALL provide a `compute_variance` function that accepts a `FinancialDocument` and returns a list of `IncomeStatementLine` instances, each containing `variance_bva` (actual minus budget) and `variance_bvf` (forecast minus budget) for each unique account/entity/period combination.
4. THE Pure_Function_Layer SHALL provide an `eliminate_intercompany` function that accepts a `FinancialDocument` and an elimination `EntityCode` and returns a new `FinancialDocument` with intercompany lines removed or netted to zero.
5. WHEN `filter_entity` is called, THE Pure_Function_Layer SHALL preserve the `accounts` and `entities` tuples and `meta` dictionary from the original `FinancialDocument` unchanged.
6. WHEN `compute_variance` is called with a `FinancialDocument` containing no lines for a given line_type, THE Pure_Function_Layer SHALL use `Decimal("0")` as the missing amount for that line_type in the variance calculation.

### Requirement 7: Frontend Pipeline Refactoring

**User Story:** As a frontend developer, I want the import/transform/export pipeline to operate on `FinancialDocument` (Zod-validated) instead of `TabularData`, so that the frontend benefits from the same typed domain model as the backend.

#### Acceptance Criteria

1. WHEN the Excel importer parses a valid budget workbook, THE Frontend SHALL produce a Zod-validated `FinancialDocument` object instead of a `TabularData` object.
2. WHEN the pipeline orchestrator passes data between import, transform, and export stages, THE Frontend SHALL use `FinancialDocument` as the inter-stage data type.
3. WHEN the CSV exporter receives a `FinancialDocument`, THE Frontend SHALL produce a CSV string with one row per `FinancialLine`.
4. WHEN the Excel exporter receives a `FinancialDocument`, THE Frontend SHALL produce an `.xlsx` file with one row per `FinancialLine`.
5. THE Frontend SHALL remove all references to `TabularData`, `ColumnDef`, `Row`, and `CellValue` from pipeline code after the migration is complete.

### Requirement 8: Serialization Round-Trip

**User Story:** As a developer, I want `FinancialDocument` to serialize to JSON and deserialize back without data loss, so that API communication and persistence preserve domain data exactly.

#### Acceptance Criteria

1. THE Backend SHALL serialize `FinancialDocument` to JSON using Pydantic's `model_dump_json()` method, producing a JSON string where `Decimal` values are serialized as strings to preserve precision.
2. THE Backend SHALL deserialize a JSON string back to a `FinancialDocument` using Pydantic's `model_validate_json()` method.
3. FOR ALL valid `FinancialDocument` instances, serializing to JSON and deserializing back SHALL produce a `FinancialDocument` equal to the original (round-trip property).
4. THE Frontend SHALL serialize `FinancialDocument` to JSON using Zod-compatible serialization where `Decimal` amounts are represented as strings.
5. FOR ALL valid `FinancialDocument` JSON payloads produced by the Backend, THE Frontend Zod schema SHALL successfully parse the payload without errors.

### Requirement 9: Backward Compatibility

**User Story:** As a user, I want existing import/export workflows to continue functioning during and after the migration, so that the refactoring does not break current functionality.

#### Acceptance Criteria

1. WHEN a user imports an Excel budget file using the existing UI flow, THE System SHALL produce the same output file content (CSV or Excel) as the pre-refactoring version for identical input data and configuration.
2. WHEN a user selects an accounting package template (Twinfield, Exact, AFAS), THE System SHALL apply the same column mappings and transformations as the pre-refactoring version.
3. THE Backend SHALL continue to serve the existing REST API endpoints (`/api/templates/*`, `/api/configurations/*`, `/api/documentation/*`) with response schemas compatible with current frontend consumers.
4. WHILE the migration is in progress, THE System SHALL support both `TabularData`-based and `FinancialDocument`-based code paths via an adapter layer that converts between the two representations.
5. WHEN the migration is complete, THE System SHALL remove the adapter layer and all `TabularData` references from production code.

### Requirement 10: Immutability Enforcement

**User Story:** As a developer, I want the domain model to enforce immutability at every level, so that financial data cannot be accidentally corrupted by in-place mutation.

#### Acceptance Criteria

1. THE Backend SHALL configure all domain model classes with `frozen=True`, causing Pydantic to raise a `ValidationError` on any field assignment attempt.
2. WHEN code needs to create a modified version of a domain model instance, THE Backend SHALL use `model_copy(update={...})` to produce a new instance with the specified field changes.
3. THE Backend SHALL use `tuple` (not `list`) for collection fields in `FinancialDocument` (`lines`, `accounts`, `entities`) to prevent in-place mutation of the collections.
4. THE Frontend SHALL use `Readonly<>` TypeScript utility types or Zod `.readonly()` on array fields in the domain model types to signal immutability intent.

### Requirement 11: Adapter Layer for Migration

**User Story:** As a developer, I want adapter functions that convert between `TabularData` and `FinancialDocument`, so that the migration can proceed incrementally without breaking existing code.

#### Acceptance Criteria

1. THE Backend SHALL provide a `tabular_to_financial_document` function that accepts a `TabularData`, a `MappingConfig`, and a `UserParams` and returns a `FinancialDocument`.
2. THE Backend SHALL provide a `financial_document_to_tabular` function that accepts a `FinancialDocument` and an `OutputTemplate` and returns a `TabularData`.
3. WHEN `tabular_to_financial_document` receives a `TabularData` with valid budget data, THE Adapter SHALL produce a `FinancialDocument` where each data row maps to a `BudgetLine` with the correct `account`, `entity`, `period`, and `amount` values.
4. WHEN `financial_document_to_tabular` receives a `FinancialDocument`, THE Adapter SHALL produce a `TabularData` where each `FinancialLine` maps to a `Row` with `CellValue` entries matching the output template columns.
5. FOR ALL valid `TabularData` inputs with valid `MappingConfig` and `UserParams`, converting to `FinancialDocument` and back to `TabularData` SHALL preserve the data values (round-trip property, modulo type normalization of cell values to strings).
