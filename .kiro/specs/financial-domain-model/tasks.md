# Implementation Plan: Financial Domain Model

## Overview

Incremental migration from `TabularData` to `FinancialDocument` as the fintran IR. Backend domain types first, then pure functions, then adapters, then frontend Zod schemas, then frontend pipeline refactoring. The adapter layer enables each stage to be migrated independently without breaking existing flows.

## Tasks

- [x] 1. Create backend domain model types in `backend/app/core/domain.py`
  - [x] 1.1 Define primitive types and enums (`AccountCode`, `EntityCode`, `Period` NewTypes, `LineType`, `AccountType`, `DebitCredit` StrEnums)
    - Create `backend/app/core/domain.py`
    - Define `AccountCode = NewType("AccountCode", str)`, `EntityCode = NewType("EntityCode", str)`, `Period = NewType("Period", str)`
    - Define `LineType(StrEnum)` with values `budget`, `actual`, `forecast`
    - Define `AccountType(StrEnum)` with values `asset`, `liability`, `equity`, `revenue`, `expense`
    - Define `DebitCredit(StrEnum)` with values `D`, `C`
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Define dimension models (`Account`, `Entity`, `Period`)
    - Define `Account(BaseModel, frozen=True)` with `code`, `description`, `account_type`, `normal_balance`, `parent_code`
    - Define `Entity(BaseModel, frozen=True)` with `code`, `description`, `is_elimination`
    - Define `Period(BaseModel, frozen=True)` with `value`, `year`, `month`, `fiscal_year`
    - _Requirements: 1.3_

  - [x] 1.3 Define core line types (`FinancialLine`, `BudgetLine`, `ActualLine`, `ForecastLine`)
    - Define `FinancialLine(BaseModel, frozen=True)` with `account`, `entity`, `period`, `amount` (Decimal), `line_type`, `currency` (default "EUR"), `memo` (optional)
    - Define `BudgetLine(FinancialLine, frozen=True)` with `line_type: Literal[LineType.BUDGET]`, `version` (default "v1")
    - Define `ActualLine(FinancialLine, frozen=True)` with `line_type: Literal[LineType.ACTUAL]`, `journal_ref` (optional)
    - Define `ForecastLine(FinancialLine, frozen=True)` with `line_type: Literal[LineType.FORECAST]`, `basis` (Literal)
    - _Requirements: 1.4, 1.5_

  - [x] 1.4 Define statement lines and `FinancialDocument`
    - Define `IncomeStatementLine(BaseModel, frozen=True)` with `account`, `entity`, `period`, `budget`, `actual`, `forecast`, `variance_bva`, `variance_bvf`
    - Define `BalanceSheetLine(BaseModel, frozen=True)` with `account`, `entity`, `period`, `balance`, `line_type`
    - Define `CashflowLine(BaseModel, frozen=True)` with `account`, `entity`, `period`, `inflow`, `outflow`, `net`, `line_type`
    - Define `FinancialDocument(BaseModel, frozen=True)` with `lines: tuple[FinancialLine, ...]`, `accounts: tuple[Account, ...]`, `entities: tuple[Entity, ...]`, `meta: dict[str, str]`
    - _Requirements: 1.6, 1.7_

  - [x] 1.5 Write property test: Immutability enforcement (Property 1)
    - **Property 1: Immutability enforcement across all domain models**
    - Create `backend/tests/test_property_domain_immutability.py`
    - Use Hypothesis to generate instances of each domain model and verify field assignment raises `ValidationError`
    - **Validates: Requirements 1.3, 1.6, 1.8, 10.1**

  - [x] 1.6 Write property test: Specialised line type Literal constraint (Property 2)
    - **Property 2: Specialised line type Literal constraint**
    - Create `backend/tests/test_property_domain_literals.py`
    - Verify `BudgetLine.line_type == "budget"`, `ActualLine.line_type == "actual"`, `ForecastLine.line_type == "forecast"`, and mismatched construction raises `ValidationError`
    - **Validates: Requirements 1.5**

  - [x] 1.7 Write property test: Tuple collections (Property 3)
    - **Property 3: FinancialDocument uses tuples for collection fields**
    - Create `backend/tests/test_property_domain_collections.py`
    - Verify `lines`, `accounts`, `entities` are `tuple` type for any valid `FinancialDocument`
    - **Validates: Requirements 1.7, 10.3**

  - [x] 1.8 Write property test: model_copy produces new instance (Property 4)
    - **Property 4: model_copy produces a new instance with updated fields**
    - Create `backend/tests/test_property_domain_copy.py`
    - Verify `model_copy(update={...})` returns new instance with updated field, original unchanged
    - **Validates: Requirements 10.2**

  - [x] 1.9 Write property test: JSON serialization round-trip (Property 7)
    - **Property 7: Backend JSON serialization round-trip**
    - Create `backend/tests/test_property_domain_serialization.py`
    - Verify `FinancialDocument.model_validate_json(doc.model_dump_json()) == doc` for all valid instances
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 2. Create Hypothesis test strategies in `backend/tests/strategies.py`
  - Define reusable Hypothesis strategies for `AccountCode`, `EntityCode`, periods, amounts, `Account`, `Entity`, `FinancialLine`, `BudgetLine`, `ActualLine`, `ForecastLine`, and `FinancialDocument`
  - These strategies are used by all property tests in tasks 1.5–1.9 and later tasks
  - _Requirements: 1.1–1.7_

- [x] 3. Checkpoint — Verify domain model types
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement pure function layer in `backend/app/core/functions.py`
  - [x] 4.1 Implement `filter_entity` and `filter_period`
    - `filter_entity(doc, entity)` returns new `FinancialDocument` with only matching entity lines, preserving `accounts`, `entities`, `meta`
    - `filter_period(doc, year)` returns new `FinancialDocument` with only lines whose period starts with the year string
    - _Requirements: 6.1, 6.2, 6.8_

  - [x] 4.2 Write property tests for filter functions (Properties 9, 10)
    - **Property 9: filter_entity returns only matching lines and preserves metadata**
    - **Property 10: filter_period returns only matching year lines**
    - Create `backend/tests/test_property_functions_filter.py`
    - **Validates: Requirements 6.1, 6.2, 6.8**

  - [x] 4.3 Implement `compute_variance`
    - Group lines by account/entity/period, sum amounts by line_type, compute `variance_bva = actual - budget`, `variance_bvf = forecast - budget`, use `Decimal("0")` for missing line types
    - Return `list[IncomeStatementLine]`
    - _Requirements: 6.3, 6.9_

  - [x] 4.4 Write property test for compute_variance (Property 11)
    - **Property 11: compute_variance produces correct variance values**
    - Create `backend/tests/test_property_functions_variance.py`
    - **Validates: Requirements 6.3, 6.9**

  - [x] 4.5 Implement `eliminate_intercompany`
    - `eliminate_intercompany(doc, elim)` returns new `FinancialDocument` with lines for the elimination entity removed
    - _Requirements: 6.4_

  - [x] 4.6 Write property test for eliminate_intercompany (Property 12)
    - **Property 12: eliminate_intercompany removes elimination entity lines**
    - Create `backend/tests/test_property_functions_eliminate.py`
    - **Validates: Requirements 6.4**

- [x] 5. Checkpoint — Verify pure function layer
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement adapter layer in `backend/app/core/adapters.py`
  - [x] 6.1 Implement `tabular_to_financial_document`
    - Accept `TabularData`, `MappingConfig`, `UserParams`
    - Map each data row to a `BudgetLine` using mapping config for account, entity, period, amount extraction
    - Extract `Account` and `Entity` dimension entries from the data
    - Populate `meta` with source info
    - Raise `ValueError` for unmappable columns
    - _Requirements: 11.1, 11.3_

  - [x] 6.2 Implement `financial_document_to_tabular`
    - Accept `FinancialDocument` and `OutputTemplate`
    - Map each `FinancialLine` to a `Row` with `CellValue` entries matching template columns
    - Handle `from_source`, `from_transform` (period_number, DC split), `from_user_param`, `fixed_null` mappings
    - _Requirements: 11.2, 11.4, 5.3, 5.4, 5.5_

  - [x] 6.3 Write property test for adapter round-trip (Property 17)
    - **Property 17: Adapter TabularData round-trip preserves data values**
    - Create `backend/tests/test_property_adapters.py`
    - **Validates: Requirements 11.3, 11.4, 11.5**

  - [x] 6.4 Write property tests for writer behaviors (Properties 13–16)
    - **Property 13: Writer output row count matches FinancialDocument lines**
    - **Property 14: from_source mapping extracts correct field values**
    - **Property 15: period_number transform extracts correct period**
    - **Property 16: DC split produces correct debit/credit based on normal_balance**
    - Create `backend/tests/test_property_writers.py`
    - **Validates: Requirements 3.2, 3.3, 5.1–5.5, 7.3, 7.4**

- [x] 7. Checkpoint — Verify adapter layer
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Create frontend Zod schemas in `frontend/src/types/domain.ts`
  - [x] 8.1 Define enum and primitive Zod schemas
    - Define `LineTypeSchema`, `AccountTypeSchema`, `DebitCreditSchema` as `z.enum()`
    - Define `AccountCodeSchema`, `EntityCodeSchema` as branded `z.string()` with `.brand<"AccountCode">()`
    - _Requirements: 2.1_

  - [x] 8.2 Define dimension and line type Zod schemas
    - Define `AccountSchema`, `EntitySchema` as `z.object({...}).readonly()`
    - Define `FinancialLineSchema`, `BudgetLineSchema`, `ActualLineSchema`, `ForecastLineSchema` as `z.object({...}).readonly()`
    - Define `IncomeStatementLineSchema`, `BalanceSheetLineSchema`, `CashflowLineSchema`
    - _Requirements: 2.2_

  - [x] 8.3 Define `FinancialDocumentSchema` and export inferred types
    - Define `FinancialDocumentSchema` with `lines`, `accounts`, `entities` as `z.array().readonly()`, `meta` as `z.record(z.string())`
    - Export `z.infer<>` types for all schemas: `FinancialDocument`, `FinancialLine`, `Account`, `Entity`, etc.
    - _Requirements: 2.2, 2.3, 10.4_

  - [x] 8.4 Write property test: Zod accepts backend JSON (Property 5)
    - **Property 5: Zod schema accepts all valid backend-produced FinancialDocument JSON**
    - Create `frontend/tests/types/test_property_domain_zod.test.ts` with fast-check arbitraries
    - Create `frontend/tests/arbitraries/domain.ts` with reusable fast-check arbitraries
    - **Validates: Requirements 2.2, 2.4, 8.5**

  - [x] 8.5 Write property test: Zod error messages (Property 6)
    - **Property 6: Zod validation surfaces descriptive errors for invalid payloads**
    - Add to `frontend/tests/types/test_property_domain_zod.test.ts`
    - Verify `.safeParse()` errors contain field path and expected type for invalid payloads
    - **Validates: Requirements 2.5**

- [x] 9. Checkpoint — Verify frontend Zod schemas
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Refactor frontend pipeline to use `FinancialDocument`
  - [x] 10.1 Update Excel importer to produce `FinancialDocument`
    - Modify `frontend/src/import/excel-importer.ts` to produce a Zod-validated `FinancialDocument` instead of `TabularData`
    - Parse budget rows into `FinancialLine` objects, extract `Account` and `Entity` dimensions
    - Validate output with `FinancialDocumentSchema.parse()`
    - _Requirements: 3.1, 7.1_

  - [x] 10.2 Update pipeline orchestrator to pass `FinancialDocument` between stages
    - Modify `frontend/src/pipeline/orchestrator.ts` to use `FinancialDocument` as the inter-stage data type
    - Update `frontend/src/pipeline/context-builder.ts` to consume `FinancialDocument`
    - _Requirements: 3.4, 3.5, 7.2_

  - [x] 10.3 Update CSV and Excel exporters to consume `FinancialDocument`
    - Modify `frontend/src/export/csv-excel-exporter.ts` to accept `FinancialDocument` and produce CSV/Excel with one row per `FinancialLine`
    - _Requirements: 3.2, 3.3, 7.3, 7.4_

  - [x] 10.4 Remove `TabularData` references from frontend pipeline code
    - Remove all imports and usages of `TabularData`, `ColumnDef`, `Row`, `CellValue` from pipeline modules
    - Verify no remaining references in `frontend/src/import/`, `frontend/src/pipeline/`, `frontend/src/export/`
    - _Requirements: 7.5_

  - [x] 10.5 Write unit tests for frontend pipeline refactoring
    - Update existing tests in `frontend/tests/import/`, `frontend/tests/pipeline/`, `frontend/tests/export/` to use `FinancialDocument`
    - Test Excel import produces valid `FinancialDocument`, orchestrator passes `FinancialDocument` between stages, exporters produce correct output
    - _Requirements: 7.1–7.5_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The adapter layer (task 6) enables incremental migration — existing code continues to work via `TabularData ↔ FinancialDocument` conversion
- Backend domain types (task 1) and strategies (task 2) must be completed before any property tests can run
- Frontend Zod schemas (task 8) must be completed before frontend pipeline refactoring (task 10)
