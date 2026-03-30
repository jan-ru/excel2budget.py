/**
 * Property test: Cancel releases pending workbook (Property 5)
 *
 * For any workbook held in the orchestrator's pending state (after an
 * `importFile` that returned `SheetSelectionNeeded`), calling
 * `cancelPendingImport()` SHALL set the internal `_pendingWorkbook` to null.
 * We verify this indirectly: `importWithSheet` should fail with the
 * "No pending workbook" error after cancellation.
 *
 * Feature: dynamic-sheet-selection, Property 5: Cancel releases pending workbook
 * Validates: Requirements 5.3
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  PipelineOrchestrator,
  isSheetSelectionNeeded,
} from "../../src/pipeline/orchestrator";

// --- Helpers ---

/** Characters safe for Excel sheet names (no :\/?*[]') */
const SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-";

/** Arbitrary for a valid Excel sheet name that is NOT "Budget". */
const nonBudgetSheetName = fc
  .stringOf(fc.constantFrom(...SAFE_CHARS), { minLength: 1, maxLength: 20 })
  .map((s) => s.trim())
  .filter((s) => s.length > 0 && s !== "Budget");

/** Required column headers for a valid budget sheet. */
const REQUIRED_HEADERS = ["Entity", "Account", "DC", "jan-26"];

/**
 * Build a workbook with non-Budget sheets, each containing valid headers
 * and at least one data row.
 */
function buildWorkbookWithSheets(sheetNames: string[]): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  for (const name of sheetNames) {
    const sheetData = [REQUIRED_HEADERS, ["E1", "A1", "D", 100]];
    const ws = XLSX.utils.aoa_to_sheet(sheetData);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }

  return wb;
}

/** Convert a workbook to a File object. */
function workbookToFile(wb: XLSX.WorkBook): File {
  const bytes = XLSX.write(wb, { type: "array", bookType: "xlsx" }) as Uint8Array;
  return new File([bytes as BlobPart], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

// --- Property 5: Cancel releases pending workbook ---

describe("Property 5: Cancel releases pending workbook", () => {
  // Feature: dynamic-sheet-selection, Property 5: Cancel releases pending workbook

  it("importWithSheet fails after cancelPendingImport", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.uniqueArray(nonBudgetSheetName, { minLength: 1, maxLength: 5 }),
        async (sheetNames) => {
          const wb = buildWorkbookWithSheets(sheetNames);
          const file = workbookToFile(wb);

          const orchestrator = new PipelineOrchestrator();

          // importFile should return SheetSelectionNeeded (no "Budget" sheet)
          const importResult = await orchestrator.importFile(file);
          expect(isSheetSelectionNeeded(importResult)).toBe(true);

          // Cancel the pending import
          orchestrator.cancelPendingImport();

          // importWithSheet should now fail — workbook was released
          const result = await orchestrator.importWithSheet(sheetNames[0]);
          expect(result).toHaveProperty("ok", false);
          if ("ok" in result && !result.ok) {
            expect(result.error).toContain("No pending workbook");
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
