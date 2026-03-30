/**
 * Property test: Auto-import when Budget sheet exists (Property 1)
 *
 * For any workbook that contains a sheet named "Budget" (with valid headers
 * and data), possibly among other sheets, calling `importFile` SHALL return
 * a successful `Result<TabularData>` (not a `SheetSelectionNeeded`), and the
 * extracted data's `metadata.sourceName` SHALL equal `"Budget"`.
 *
 * Feature: dynamic-sheet-selection, Property 1: Auto-import when Budget sheet exists
 * Validates: Requirements 1.1, 1.2
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
 * Build a workbook that always contains a "Budget" sheet with valid headers
 * and at least one data row, plus any number of extra sheets.
 */
function buildWorkbookWithBudget(extraSheetNames: string[]): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  // Add the Budget sheet with valid headers and one data row
  const budgetData = [
    REQUIRED_HEADERS,
    ["E1", "A1", "D", 100],
  ];
  const budgetWs = XLSX.utils.aoa_to_sheet(budgetData);
  XLSX.utils.book_append_sheet(wb, budgetWs, "Budget");

  // Add extra sheets with minimal content
  for (const name of extraSheetNames) {
    const ws = XLSX.utils.aoa_to_sheet([["col1"], ["val1"]]);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }

  return wb;
}

/** Convert a workbook to a File object (round-trip through XLSX.write). */
function workbookToFile(wb: XLSX.WorkBook): File {
  const bytes: Uint8Array = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new File([bytes], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

// --- Property 1: Auto-import when Budget sheet exists ---

describe("Property 1: Auto-import when Budget sheet exists", () => {
  // Feature: dynamic-sheet-selection, Property 1: Auto-import when Budget sheet exists

  it("importFile returns successful Result<TabularData> with sourceName 'Budget'", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.uniqueArray(nonBudgetSheetName, { minLength: 0, maxLength: 5 }),
        async (extraSheets) => {
          const wb = buildWorkbookWithBudget(extraSheets);
          const file = workbookToFile(wb);

          const orchestrator = new PipelineOrchestrator();
          const result = await orchestrator.importFile(file);

          // Should NOT be a SheetSelectionNeeded
          expect(isSheetSelectionNeeded(result)).toBe(false);

          // Should be a successful result
          expect(result).toHaveProperty("ok", true);

          if ("ok" in result && result.ok) {
            // metadata.sourceName must be "Budget"
            expect(result.data.metadata.sourceName).toBe("Budget");
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
