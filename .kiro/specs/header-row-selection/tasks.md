# Implementation Plan: Header Row Selection

## Overview

Add header row detection and selection to the Excel import pipeline. After sheet resolution, the importer scans the first 20 rows for rows containing all required columns (Entity, Account, DC). If row 0 matches, import proceeds automatically. If exactly one other row matches, it auto-selects. If zero or multiple rows match, the user picks from a Header_Row_Selector dropdown. The Upload_Screen gains a progressive summary showing resolved import variables. All changes are frontend-only TypeScript, tested with vitest + fast-check.

## Tasks

- [-] 1. Add header row scanning to Excel Importer
  - [x] 1.1 Add `rowContainsRequiredColumns` helper to `frontend/src/import/excel-importer.ts`
    - Export function `rowContainsRequiredColumns(row: unknown[], requiredColumns?: readonly string[]): boolean`
    - Default `requiredColumns` to `["Entity", "Account", "DC"]`
    - Use case-insensitive matching consistent with the existing `findColumn` helper
    - Convert each cell to trimmed string before comparison
    - _Requirements: 2.5_

  - [x] 1.2 Add `scanForHeaderRow` function to `frontend/src/import/excel-importer.ts`
    - Export `HeaderScanResult` interface with `candidateRows: number[]` and `rawPreview: unknown[][]`
    - Export function `scanForHeaderRow(workbook: XLSX.WorkBook, sheetName: string): HeaderScanResult | ParseError`
    - Read sheet with `sheet_to_json(ws, { header: 1, defval: null })` to get raw rows
    - Scan rows 0 through min(19, length-1), calling `rowContainsRequiredColumns` on each
    - Return `candidateRows` (zero-based indices of matching rows) and `rawPreview` (first 20 rows)
    - Return `ParseError` if sheet not found or empty
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 7.2_

  - [x] 1.3 Modify `extractBudgetData` to accept optional `headerRowIndex` parameter
    - Add third parameter `headerRowIndex?: number` (defaults to 0)
    - Use `raw[headerRowIndex]` as the header row instead of `raw[0]`
    - Data rows are `raw.slice(headerRowIndex + 1)` — rows above header are ignored
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 1.4 Modify `extractMappingConfig` to accept optional `headerRowIndex` parameter
    - Add third parameter `headerRowIndex?: number` (defaults to 0)
    - Use `raw[headerRowIndex]` as the column names source
    - Return `MappingError` with `missingColumns` if the specified row lacks required columns
    - _Requirements: 4.1, 4.4_

  - [x] 1.5 Write property test: Row 0 auto-detection (Property 1)
    - **Property 1: Row 0 auto-detection**
    - Generate sheets with required columns in row 0 using random case variations; verify `scanForHeaderRow` returns `candidateRows` including index 0
    - **Validates: Requirements 1.1**

  - [x] 1.6 Write property test: Scan finds all and only matching rows (Property 2)
    - **Property 2: Scan finds all and only matching rows**
    - Generate sheets with known placement of required-column rows in positions 0–19; verify `candidateRows` matches exactly the expected indices
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

- [x] 2. Checkpoint — Ensure importer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Extend Pipeline Orchestrator with header row selection flow
  - [x] 3.1 Add `HeaderSelectionNeeded` type and type guard to `frontend/src/pipeline/orchestrator.ts`
    - Define `HeaderSelectionNeeded` interface with `needsHeaderSelection: true`, `candidateRows: number[]`, `rawPreview: unknown[][]`
    - Extend `ImportResult` union to include `HeaderSelectionNeeded`
    - Export `isHeaderSelectionNeeded` type guard function
    - _Requirements: 3.1_

  - [x] 3.2 Add `_pendingSheetName` state and modify `importFile` to scan for header row
    - Add `private _pendingSheetName: string | null = null` field
    - After sheet resolution (either "Budget" auto-detected or from `importWithSheet`), call `scanForHeaderRow`
    - If row 0 is in candidates: proceed with extraction using `headerRowIndex: 0`
    - If exactly one candidate (not row 0): auto-select that row for extraction
    - If zero or multiple candidates: store `_pendingSheetName`, return `HeaderSelectionNeeded`
    - Update `cancelPendingImport()` and `reset()` to also clear `_pendingSheetName`
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Modify `importWithSheet` to scan for header row after sheet extraction
    - After resolving the sheet, call `scanForHeaderRow` instead of directly extracting
    - Apply the same auto-detection logic as `importFile` (row 0 → auto, one candidate → auto, else → prompt)
    - Return `HeaderSelectionNeeded` when user input is needed; change return type to `Promise<ImportResult>`
    - Store `_pendingSheetName` when header selection is needed
    - _Requirements: 6.2_

  - [x] 3.4 Add `importWithHeaderRow(headerRowIndex: number)` method
    - If `_pendingWorkbook` or `_pendingSheetName` is null, return error result
    - Call `extractBudgetData(wb, sheetName, headerRowIndex)` and `extractMappingConfig(wb, sheetName, headerRowIndex)`
    - On success: store data/mapping, clear pending state, return `{ ok: true, data }`
    - On failure: return error result, keep pending state so user can retry
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 3.5 Write property test: Extraction with header row index (Property 4)
    - **Property 4: Extraction with header row index**
    - Generate sheets with required columns at a random row; call `extractBudgetData` with that index; verify columns match the header row and data rows are all rows after it
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 3.6 Write property test: Invalid header row returns MappingError (Property 5)
    - **Property 5: Invalid header row returns MappingError**
    - Generate sheets; pick a row without required columns; call `extractMappingConfig` with that index; verify `MappingError` with non-empty `missingColumns`
    - **Validates: Requirements 4.4**

  - [x] 3.7 Write property test: Backward compatibility — full auto-import (Property 6)
    - **Property 6: Backward compatibility — full auto-import**
    - Generate workbooks with "Budget" sheet, headers in row 0, valid month columns, data; verify `importFile` returns successful `Result<TabularData>` without `SheetSelectionNeeded` or `HeaderSelectionNeeded`
    - **Validates: Requirements 1.2, 6.1**

  - [x] 3.8 Write property test: Sheet selection then auto header detection (Property 7)
    - **Property 7: Sheet selection then auto header detection**
    - Generate workbooks without "Budget", one sheet with headers in row 0 + month columns; call `importWithSheet`; verify successful result without `HeaderSelectionNeeded`
    - **Validates: Requirements 6.2**

- [x] 4. Checkpoint — Ensure orchestrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create Header Row Selector UI component
  - [x] 5.1 Create `frontend/src/ui/components/header-row-selector.ts`
    - Export `HeaderRowSelectorOptions` interface with `candidateRows`, `rawPreview`, `onConfirm`, `onCancel`
    - Export `createHeaderRowSelector(options): HTMLElement`
    - When `candidateRows` is non-empty: dropdown contains only those rows
    - When `candidateRows` is empty: dropdown contains rows 0 through min(19, rawPreview.length-1)
    - Each option label: `"Row {n}: {cell1}, {cell2}, {cell3}"` (1-based row number, first 3 cell values)
    - "Confirm" button disabled until a row is selected; "Cancel" calls `onCancel`
    - On confirm: calls `onConfirm(selectedZeroBasedIndex)`
    - Add `aria-label` attributes for accessibility
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 5.2 Write property test: Header row selector renders correct options (Property 3)
    - **Property 3: Header row selector renders correct options with previews**
    - Generate random candidate indices and raw preview arrays; render component; verify option count, labels with 1-based numbering, and first 3 cell values
    - **Validates: Requirements 3.2, 3.3**

  - [x] 5.3 Write unit tests for Header Row Selector behavior
    - Test: Confirm button disabled on initial render (3.6)
    - Test: Confirm button enabled after selecting a row
    - Test: Cancel calls `onCancel` (3.5)
    - Test: Confirm calls `onConfirm` with correct zero-based index (3.4)
    - Test: Empty candidates shows all rows up to 20 (3.3)
    - _Requirements: 3.3, 3.4, 3.5, 3.6_

- [x] 6. Integrate header row selection and progressive summary into Upload Screen
  - [x] 6.1 Add `updateProgressSummary` helper and progress summary section to `frontend/src/ui/screens/upload.ts`
    - Create a summary container element showing label/value pairs
    - Display filename after file selection (5.1)
    - Display sheet name after sheet resolution (5.2)
    - Display header row (1-based) after header row resolution (5.3)
    - Show each item only after the corresponding step completes (5.4)
    - Clear all items on cancel/reset (5.5)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 6.2 Handle `HeaderSelectionNeeded` result in Upload Screen
    - Import `isHeaderSelectionNeeded` from orchestrator and `createHeaderRowSelector` from components
    - After `importFile` or `importWithSheet`, check for `HeaderSelectionNeeded`
    - If header selection needed: render `Header_Row_Selector`, update summary
    - On confirm: call `orchestrator.importWithHeaderRow(index)`, handle success or error
    - On error after header selection: show error banner, keep Header_Row_Selector visible (7.1)
    - On cancel: call `orchestrator.cancelPendingImport()`, clear summary, reset UI (7.3)
    - _Requirements: 3.1, 4.1, 7.1, 7.3_

  - [x] 6.3 Write unit tests for Upload Screen header row integration
    - Test: Header_Row_Selector appears when `HeaderSelectionNeeded` returned (3.1)
    - Test: Error after header selection returns to selector (7.1)
    - Test: Cancel resets to initial state and clears summary (7.3)
    - Test: Progressive summary shows filename, sheet, header row as they resolve (5.1, 5.2, 5.3)
    - Test: Summary cleared on cancel (5.5)
    - _Requirements: 3.1, 5.1, 5.2, 5.3, 5.5, 7.1, 7.3_

- [x] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All code is TypeScript, tested with vitest + fast-check
- No backend changes required — all modifications are in the frontend
