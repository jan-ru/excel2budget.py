# Implementation Plan: Data Conversion Tool

## Overview

Browser-based budget data conversion pipeline using IronCalc WASM (spreadsheet preview), DuckDB WASM (SQL transformation), and Python for all application logic. Transforms wide-format Excel budget files into accounting package import formats (Twinfield, Exact, Afas). Includes a reusable Documentation Module generating 7 artifacts per configuration.

## Tasks

- [ ] 1. Define core data models and types
  - [x] 1.1 Create core type definitions in `src/core/types.py`
    - Define `DataType` enum, `CellValue` variant type, `ColumnDef`, `Row`, `DataMetadata`, `TabularData` dataclasses
    - Define `MappingConfig`, `MonthColumnDef`, `UserParams`, `OutputTemplate`, `TemplateColumnDef`, `ColumnSourceMapping` types
    - Define `TransformResult` (Success/Error), `FileFormat` enum, `TableRef`, `ConversionConfiguration`
    - Define `ValidationResult` type for template validation
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 1.2 Implement TabularData validation functions in `src/core/validation.py`
    - Validate row length matches column count, column name uniqueness, rowCount consistency
    - Validate MappingConfig: monthColumns count 1–12, unique periodNumbers in 1–12, referenced columns exist
    - Validate UserParams: non-empty budgetcode, positive year
    - _Requirements: 12.1, 12.2, 12.3, 2.2, 2.5, 4.2, 4.3_

  - [x] 1.3 Write property tests for TabularData validation
    - **Property 14: TabularData structural invariants** — every Row has exactly as many values as columns, column names unique, rowCount equals actual row count
    - **Validates: Requirements 12.1, 12.2, 12.3**

  - [x] 1.4 Write property tests for MappingConfig and UserParams validation
    - **Property 13: MappingConfig validity invariant** — month columns 1–12, unique periodNumbers, referenced columns exist
    - **Property 15: UserParams validation** — empty budgetcode or non-positive year rejected
    - **Validates: Requirements 2.2, 2.5, 4.2, 4.3**

- [x] 2. Implement Template Registry
  - [x] 2.1 Create template registry in `src/templates/registry.py`
    - Implement `getTemplate(packageName, templateName)`, `listPackages()`, `listTemplates(packageName)`, `validateOutput(data, template)`
    - Return `TemplateError` for unknown package/template combinations
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.2 Define Twinfield budget template in `src/templates/twinfield/budget.py`
    - Define the 13-column Twinfield schema: Entity, Budgetcode, Grootboekrekening, Kostenplaats, Project, Jaar, Periode, Debet, Credit, Hvlhd1 Debet, Hvlhd1 Credit, Hvlhd2 Debet, Hvlhd2 Credit
    - Define `ColumnSourceMapping` for each column (FromSource, FromUserParam, FromTransform, FixedNull)
    - _Requirements: 3.3, 5.10_

  - [x] 2.3 Define Exact and Afas budget template stubs in `src/templates/exact/budget.py` and `src/templates/afas/budget.py`
    - Create placeholder templates with basic column schemas (to be refined when specs are available)
    - _Requirements: 3.1, 3.2_

  - [x] 2.4 Write property test for OutputTemplate completeness
    - **Property 17: OutputTemplate completeness** — every valid package/template returns non-empty columns with defined names, types, and source mappings
    - **Validates: Requirement 3.3**

- [x] 3. Implement DuckDB WASM Engine
  - [x] 3.1 Create DuckDB engine wrapper in `src/engine/duckdb/engine.py`
    - Implement `initialize()`, `registerTable(db, data, tableName)`, `executeSQL(db, sql)`, `dropTable(db, tableName)`, `listTables(db)`
    - Validate table names against pattern `[a-zA-Z_][a-zA-Z0-9_]*`
    - Map `DataType` enum to DuckDB SQL types (VARCHAR, BIGINT, DOUBLE, BOOLEAN, DATE, TIMESTAMP)
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 3.2 Write property tests for DuckDB registration
    - **Property 7: DuckDB registration round-trip** — register TabularData, SELECT all, verify same schema/values/row count
    - **Property 19: Table name validation** — names not matching `[a-zA-Z_][a-zA-Z0-9_]*` are rejected
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 4. Implement Excel Importer
  - [x] 4.1 Create Excel importer in `src/modules/excel2budget/importer.py`
    - Implement `parseExcelFile(rawBytes)`, `extractBudgetData(workbook, sheetName)`, `extractMappingConfig(workbook)`, `detectMonthColumns(data, config)`
    - Return `ParseError` for invalid .xlsx or missing Budget sheet (listing available sheets)
    - Return `MappingError` when Entity, Account, or DC columns cannot be identified
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.2 Write unit tests for Excel importer
    - Test valid .xlsx parsing, missing Budget sheet error, invalid file format error
    - Test mapping extraction with valid and invalid column layouts
    - Test month column detection with various naming conventions
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3, 2.4_

- [x] 5. Implement SQL Generation and Budget Transformation
  - [x] 5.1 Create SQL generator in `src/modules/excel2budget/sql_generator.py`
    - Implement `generateTransformSQL(mappingConfig, template, userParams)` producing DuckDB SQL
    - Generate UNPIVOT clause for month columns, CASE-based period extraction, DC-based Debet/Credit split
    - Add fixed columns (Budgetcode from userParams, null placeholders for Kostenplaats, Project, Hvlhd*)
    - Use `quoteIdentifier()` to escape column names and prevent SQL injection
    - Ensure generated SQL is SELECT-only (no DDL/DML)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 5.1, 5.3, 5.4, 5.6, 5.7, 5.8_

  - [-] 5.2 Write property tests for SQL generation
    - **Property 11: Generated SQL validity and safety** — valid DuckDB SQL, SELECT-only, references only "budget" table
    - **Property 12: SQL injection prevention** — adversarial column names with SQL metacharacters are properly escaped/rejected
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [x] 5.3 Implement pipeline orchestrator in `src/modules/excel2budget/pipeline.py`
    - Implement `importBudgetFile(rawBytes)`, `runBudgetTransformation(mappingConfig, template, userParams)`, `exportData(sourceRef, format)`
    - Wire together Excel importer, DuckDB engine, template registry, and format exporter
    - Filter null-account rows before unpivot
    - Detect and report invalid DC values with row positions
    - Record date stamps in DataMetadata (importedAt, transformedAt, exportedAt)
    - _Requirements: 5.1, 5.2, 5.9, 5.10, 14.1, 10.1, 10.2, 19.1, 19.2_

  - [x] 5.4 Write property tests for budget transformation
    - **Property 1: Unpivot row count** — R rows × M month columns = R×M output rows
    - **Property 2: Debet/Credit split correctness** — DC="D" → Debet=ROUND(Value,4), Credit=null; DC="C" → Credit=ROUND(ABS(Value),4), Debet=null
    - **Property 3: Period range validity** — Periode in 1–12, matches source month column periodNumber
    - **Property 4: Fixed field propagation** — Budgetcode and Jaar match userParams in every row
    - **Property 5: Null account filtering** — no output row has null Grootboekrekening
    - **Property 6: Column schema conformance** — output columns match OutputTemplate in name, order, types
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10**

  - [x] 5.5 Write property tests for source immutability and determinism
    - **Property 8: Source data immutability** — budget table unchanged after transformation
    - **Property 9: Transformation determinism** — same inputs produce identical output
    - **Property 16: Invalid DC value detection** — non-D/C values produce TransformResult.Error with row positions
    - **Validates: Requirements 10.1, 10.2, 11.1, 14.1**

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement IronCalc Spreadsheet Engine Integration
  - [x] 7.1 Create IronCalc engine wrapper in `src/engine/ironcalc/engine.py`
    - Implement `loadExcelFile(rawBytes)`, `loadData(data, sheetName)`, `getCellValue()`, `setCellValue()`, `exportSheetData()`, `getSheetNames()`
    - Integrate with IronCalc WASM for spreadsheet rendering
    - _Requirements: 1.4, 8.1_

  - [x] 7.2 Implement content sanitization in `src/engine/ironcalc/sanitizer.py`
    - Sanitize all cell values before rendering to prevent XSS
    - Strip or escape HTML tags, script elements, event handlers
    - _Requirements: 16.1_

  - [x] 7.3 Write property test for XSS sanitization
    - **Property 18: XSS sanitization** — strings with HTML/script tags produce output without executable script content
    - **Validates: Requirement 16.1**

- [x] 8. Implement Format Exporter
  - [x] 8.1 Create CSV and Excel exporters in `src/export/exporter.py`
    - Implement `exportToCSV(data)` and `exportToExcel(data, template)`
    - Preserve column ordering from OutputTemplate
    - Include export date stamp in metadata
    - Generate downloadable blobs
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 19.3_

  - [x] 8.2 Write property test for export round-trip
    - **Property 10: Export round-trip** — export and re-parse preserves column ordering, row count, and data values
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 9. Implement Documentation Module
  - [x] 9.1 Define ApplicationContext builder in `src/modules/excel2budget/context_builder.py`
    - Implement `buildApplicationContext(config, sourceData, transformedData, mappingConfig, template, sql)` → `ApplicationContext`
    - Populate all fields: identity, systems (source/target/intermediary), process steps, data descriptions, transform descriptor, control totals, user instruction steps
    - _Requirements: 17 (General criteria 4)_

  - [x] 9.2 Implement Control Table Generator in `src/documentation/control_table.py`
    - Implement `generateControlTable(context)` using `ControlTotals` from ApplicationContext
    - Compute input value totals, output Debet/Credit totals, balance checks
    - _Requirements: 17.6.1, 17.6.2, 17.6.3, 17.6.4, 17.6.5_

  - [x] 9.3 Write property tests for control table
    - **Property 20: Control table balance** — all balanceChecks have passed=true for successful transformations
    - **Property 21: Control table row count consistency** — outputRowCount = inputRowCount × monthColumnCount
    - **Validates: Requirements 17.6.2, 17.6.3, 17.6.4, 17.6.5, 5.2**

  - [x] 9.4 Implement Diagram Generator in `src/documentation/diagram_generator.py`
    - Implement `generateArchiMateDiagram(context, archimateTemplate)` and `generateBPMNDiagram(context, bpmnTemplate)`
    - Populate templates with context-specific values (source system, target system, process steps)
    - _Requirements: 17.1.1, 17.1.2, 17.1.3, 17.2.1, 17.2.2, 17.2.3_

  - [x] 9.5 Write property tests for diagram generation
    - **Property 25: ArchiMate diagram generation** — diagram contains source system, conversion tool, and target accounting package
    - **Property 26: BPMN diagram generation** — diagram contains all 6 process steps
    - **Validates: Requirements 17.1.1, 17.1.2, 17.1.3, 17.2.1, 17.2.2, 17.2.3**

  - [x] 9.6 Implement Description Generator in `src/documentation/description_generator.py`
    - Implement `generateInputDescription(context)`, `generateOutputDescription(context)`, `generateTransformDescription(context)`
    - Input description: source columns, types, mapping assignments
    - Output description: target columns, types, ordering, fixed values
    - Transform description: unpivot, DC split, column renaming, generated SQL
    - _Requirements: 17.3.1, 17.3.2, 17.3.3, 17.4.1, 17.4.2, 17.4.3, 17.5.1, 17.5.2, 17.5.3_

  - [x] 9.7 Write property tests for description generators
    - **Property 28: Input description accuracy** — lists all source columns, types, mapping assignments
    - **Property 29: Output description accuracy** — lists all target columns, types, ordering, fixed values
    - **Property 30: Transform description accuracy** — includes unpivot, DC split, column renaming, SQL
    - **Validates: Requirements 17.3.2, 17.3.3, 17.4.2, 17.4.3, 17.5.2, 17.5.3**

  - [x] 9.8 Implement User Instruction Generator in `src/documentation/user_instruction.py`
    - Implement `generateUserInstruction(context)` producing step-by-step guide
    - Reference specific accounting package and template
    - _Requirements: 17.7.1, 17.7.2, 17.7.3_

  - [x] 9.9 Write property test for user instruction
    - **Property 31: User instruction specificity** — references specific accounting package/template, includes all process steps
    - **Validates: Requirements 17.7.2, 17.7.3**

  - [x] 9.10 Implement Documentation Module orchestrator in `src/documentation/module.py`
    - Implement `generateDocumentationPack(context)` → `DocumentationPack` with all 7 artifacts
    - Wire together diagram generator, control table generator, description generator, user instruction generator
    - _Requirements: 17 (General criteria 1, 2, 3)_

  - [x] 9.11 Write property test for documentation pack completeness
    - **Property 27: Documentation pack completeness** — pack contains all 7 non-null artifacts with dates
    - **Validates: Requirement 17 (General criteria)**

- [x] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement PDF Exporter
  - [x] 11.1 Create PDF exporter in `src/export/pdf_exporter.py`
    - Implement `exportScreenToPDF(screenContent, metadata)` producing PDF bytes
    - Include date stamp, configuration name, accounting package, template in PDF
    - Support screen types: spreadsheet, diagram, control table
    - _Requirements: 20.1, 20.2, 20.3, 20.4_

  - [x] 11.2 Write property test for PDF export
    - **Property 24: PDF export availability** — produces non-empty valid PDF with screen content and date stamp
    - **Validates: Requirements 20.1, 20.2, 20.3, 20.4**

- [x] 12. Implement Browser UI
  - [x] 12.1 Create main UI shell in `src/ui/app.py`
    - Implement file upload screen, template selection, parameter input, transformation trigger, output preview, export actions
    - Display current date on every screen
    - Add "Download as PDF" action on every screen
    - _Requirements: 18.1, 18.2, 20.1_

  - [x] 12.2 Wire UI to pipeline orchestrator and documentation module
    - Connect file upload → `importBudgetFile()` → IronCalc preview
    - Connect template selection → `getTemplate()` → parameter form
    - Connect transform button → `runBudgetTransformation()` → output preview
    - Connect export buttons → `exportData()` / `exportScreenToPDF()`
    - Connect documentation tab → `generateDocumentationPack()` → render all 7 artifacts
    - _Requirements: 1.4, 8.1, 8.2, 17 (General criteria 1, 2)_

  - [x] 12.3 Write property tests for date display and date stamping
    - **Property 22: Date presence on all screens** — every rendered screen includes a visible date
    - **Property 23: Data date stamping completeness** — metadata contains importedAt, transformedAt, exportedAt at appropriate stages
    - **Validates: Requirements 18.1, 18.2, 19.1, 19.2, 19.3**

- [x] 13. Implement Memory Safety and Client-Side Constraints
  - [x] 13.1 Add file size validation and memory monitoring in `src/core/memory.py`
    - Validate file sizes before parsing to prevent memory exhaustion
    - Raise `MemoryError` with current usage and estimated requirement when WASM limits exceeded
    - Ensure no data is transmitted to any server
    - _Requirements: 15.1, 15.2, 13.1, 13.2_

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Python is the primary implementation language; IronCalc (Rust/WASM) and DuckDB (WASM) are used as engine dependencies
- The Documentation Module communicates via the generic `ApplicationContext` interface — no dependency on application-specific types
