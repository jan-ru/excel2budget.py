# Implementation Plan: Dynamic Sheet Selection

## Overview

Add dynamic sheet selection to the Excel import flow. When a workbook contains a "Budget" sheet, import proceeds automatically (backward compatible). When no "Budget" sheet exists, the orchestrator signals the UI to show a sheet selector dropdown. The user picks a sheet or cancels. All changes are frontend-only TypeScript, tested with vitest + fast-check.

## Tasks

- [x] 1. Add sheet helper functions to Excel Importer
  - [x] 1.1 Add `getSheetNames` and `hasSheet` exports to `frontend/src/import/excel-importer.ts`
    - `getSheetNames(workbook: XLSX.WorkBook): string[]` returns `workbook.SheetNames`
    - `hasSheet(workbook: XLSX.WorkBook, name: string): boolean` returns `workbook.SheetNames.includes(name)`
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 1.2 Write property test for sheet name list identity
    - **Property 2: Sheet name list identity**
    - Generate workbooks without a "Budget" sheet; verify `getSheetNames` returns the exact same array (elements and order) as `workbook.SheetNames`
    - **Validates: Requirements 2.1, 2.2, 2.3**

- [-] 2. Extend Pipeline Orchestrator with sheet selection flow
  - [x] 2.1 Add `SheetSelectionNeeded` type, `ImportResult` union, and `isSheetSelectionNeeded` type guard to `frontend/src/pipeline/orchestrator.ts`
    - Define `SheetSelectionNeeded` interface with `needsSelection: true` and `sheetNames: string[]`
    - Define `ImportResult = Result<TabularData> | SheetSelectionNeeded`
    - Export `isSheetSelectionNeeded` type guard function
    - _Requirements: 2.1, 3.1_

  - [x] 2.2 Add `_pendingWorkbook` state and modify `importFile` to return `SheetSelectionNeeded` when no "Budget" sheet exists
    - Add `private _pendingWorkbook: XLSX.WorkBook | null = null` field
    - After `parseExcelFile`, check `hasSheet(workbook, "Budget")`
    - If "Budget" exists: proceed with existing extraction flow (unchanged)
    - If "Budget" missing: store workbook in `_pendingWorkbook`, return `{ needsSelection: true, sheetNames: getSheetNames(workbook) }`
    - If workbook has zero sheets: return `{ ok: false, error: "Workbook contains no sheets" }`
    - Update `reset()` to also set `_pendingWorkbook = null`
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 6.1_

  - [x] 2.3 Add `importWithSheet(sheetName: string)` method to `PipelineOrchestrator`
    - If `_pendingWorkbook` is null, return `{ ok: false, error: "No pending workbook. Call importFile() first." }`
    - Call `extractBudgetData(_pendingWorkbook, sheetName)` and `extractMappingConfig(_pendingWorkbook, sheetName)`
    - On success: store data/mapping, set `_pendingWorkbook = null`, return `{ ok: true, data }`
    - On failure: return error result (keep `_pendingWorkbook` so user can retry with another sheet)
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 2.4 Add `cancelPendingImport()` method to `PipelineOrchestrator`
    - Set `_pendingWorkbook = null`
    - Safe to call anytime (no-op if no pending workbook)
    - _Requirements: 5.3_

  - [x] 2.5 Write property test for auto-import when Budget sheet exists
    - **Property 1: Auto-import when Budget sheet exists**
    - Generate workbooks containing a "Budget" sheet (with valid headers and data) plus random other sheets; verify `importFile` returns `Result<TabularData>` with `metadata.sourceName === "Budget"`
    - **Validates: Requirements 1.1, 1.2**

  - [x] 2.6 Write property test for import with selected sheet
    - **Property 4: Import with selected sheet extracts correct data**
    - Generate workbooks with multiple non-empty sheets (valid headers); pick a random sheet name; call `importWithSheet`; verify result is successful with `metadata.sourceName` equal to the chosen name
    - **Validates: Requirements 4.1, 4.2**

  - [x] 2.7 Write property test for cancel releases pending workbook
    - **Property 5: Cancel releases pending workbook**
    - Generate workbooks without "Budget"; call `importFile` to trigger pending state; call `cancelPendingImport()`; verify `_pendingWorkbook` is null (via attempting `importWithSheet` which should fail)
    - **Validates: Requirements 5.3**

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create Sheet Selector UI component
  - [x] 4.1 Create `frontend/src/ui/components/sheet-selector.ts`
    - Export `SheetSelectorOptions` interface: `{ sheetNames: string[], onConfirm: (name: string) => void, onCancel: () => void }`
    - Export `createSheetSelector(options: SheetSelectorOptions): HTMLElement`
    - Render a `<select>` with a disabled placeholder option ("Select a sheet…") and one `<option>` per sheet name in order
    - Render "Confirm" button (disabled until a real sheet is selected) and "Cancel" button
    - "Confirm" calls `onConfirm(selectedValue)`, "Cancel" calls `onCancel()`
    - Add appropriate `aria-label` attributes for accessibility
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [x] 4.2 Write property test for sheet selector rendering
    - **Property 3: Sheet selector renders all provided names**
    - Generate non-empty arrays of non-empty strings; call `createSheetSelector`; count `<option>` elements (excluding placeholder); verify count and order match input array
    - **Validates: Requirements 3.2**

  - [x] 4.3 Write unit tests for Sheet Selector behavior
    - Test: Confirm button is disabled on initial render (3.5)
    - Test: Confirm button becomes enabled after selecting a sheet
    - Test: Cancel button calls `onCancel`
    - Test: Confirm button calls `onConfirm` with the selected sheet name (3.3)
    - _Requirements: 3.3, 3.4, 3.5_

- [x] 5. Integrate sheet selection into Upload Screen
  - [x] 5.1 Update `frontend/src/ui/screens/upload.ts` to handle `SheetSelectionNeeded` result
    - Import `isSheetSelectionNeeded` from orchestrator and `createSheetSelector` from components
    - In the file input `change` handler, check if result is `SheetSelectionNeeded`
    - If so: render `createSheetSelector` into the content area with the returned `sheetNames`
    - On confirm: call `orchestrator.importWithSheet(name)`, handle success (navigate to preview) or error (show error, keep selector visible)
    - On cancel: call `orchestrator.cancelPendingImport()`, reset UI to initial upload state (clear file input, clear status)
    - _Requirements: 3.1, 4.1, 5.1, 5.2, 6.2_

  - [x] 5.2 Write unit tests for Upload Screen sheet selection integration
    - Test: Sheet selector appears when `importFile` returns `SheetSelectionNeeded`
    - Test: Successful sheet selection navigates to preview
    - Test: Failed sheet selection shows error and keeps selector visible
    - Test: Cancel resets to initial upload state
    - _Requirements: 3.1, 5.1, 5.2, 6.2_

- [x] 6. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All code is TypeScript, tested with vitest + fast-check
- No backend changes required — all modifications are in the frontend
